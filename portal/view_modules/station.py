import csv
import secrets
from collections import defaultdict

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from portal.model_modules.station import StationCredential, StationDevice, WorkShiftEntry
from portal.model_modules.people import Person
from portal.models import AuditEvent
from portal.station_forms import (
    StationActivationForm,
    StationClockInForm,
    StationCredentialForm,
    StationDeviceForm,
    StationPinForm,
    WorkShiftReviewForm,
)
from portal.view_modules.common import _require_manage, _team


STATION_DEVICE_SESSION_KEY = "arenaline_station_device_id"
STATION_PERSON_SESSION_KEY = "arenaline_station_person_id"
STATION_PERSON_AUTH_AT_KEY = "arenaline_station_person_auth_at"
STATION_PIN_ATTEMPTS_SESSION_KEY = "arenaline_station_pin_attempts"
STATION_PERSON_AUTH_SECONDS = 120
STATION_PIN_MAX_ATTEMPTS = 5
STATION_PIN_LOCK_SECONDS = 300


def _station_device(request):
    device_id = request.session.get(STATION_DEVICE_SESSION_KEY)
    if not device_id:
        return None
    device = StationDevice.objects.filter(pk=device_id, active=True).select_related("team").first()
    if not device:
        request.session.pop(STATION_DEVICE_SESSION_KEY, None)
        return None
    StationDevice.objects.filter(pk=device.pk).update(last_seen_at=timezone.now())
    return device


def _clear_station_person(request):
    request.session.pop(STATION_PERSON_SESSION_KEY, None)
    request.session.pop(STATION_PERSON_AUTH_AT_KEY, None)


def _station_person(request, device):
    person_id = request.session.get(STATION_PERSON_SESSION_KEY)
    auth_at = request.session.get(STATION_PERSON_AUTH_AT_KEY)
    if not person_id or not auth_at:
        return None
    if timezone.now().timestamp() - float(auth_at) > STATION_PERSON_AUTH_SECONDS:
        _clear_station_person(request)
        return None
    return Person.objects.filter(pk=person_id, team=device.team, active=True).first()


def _shift_minutes(shift):
    if not shift.clock_out:
        return 0
    return max(0, int((shift.clock_out - shift.clock_in).total_seconds() // 60))


def _format_minutes(minutes):
    hours, remainder = divmod(int(minutes or 0), 60)
    if hours and remainder:
        return f"{hours}h {remainder}m"
    if hours:
        return f"{hours}h"
    return f"{remainder}m"


def _audit_station(*, team, action, entity_type, entity_id=None, entity_label="", summary="", details=None, actor=None):
    AuditEvent.objects.create(
        team=team,
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_label=(entity_label or entity_type)[:255],
        summary=(summary or action.replace("_", " ").title())[:255],
        details=details or {},
    )


def _audit_shift(team, actor, action, shift, details):
    _audit_station(
        team=team,
        actor=actor,
        action=action,
        entity_type="WorkShiftEntry",
        entity_id=shift.pk,
        entity_label=str(shift),
        summary=f"{action.replace('_', ' ').title()} — {shift.person.display_name}",
        details=details,
    )


def _pin_attempt_key(device, person_id):
    return f"{device.pk}:{person_id}"


def _pin_lock_remaining(request, device, person_id):
    attempts = request.session.get(STATION_PIN_ATTEMPTS_SESSION_KEY, {})
    state = attempts.get(_pin_attempt_key(device, person_id), {})
    locked_until = float(state.get("locked_until") or 0)
    now = timezone.now().timestamp()
    if locked_until > now:
        return max(1, int(locked_until - now))
    if locked_until:
        attempts.pop(_pin_attempt_key(device, person_id), None)
        request.session[STATION_PIN_ATTEMPTS_SESSION_KEY] = attempts
        request.session.modified = True
    return 0


def _record_pin_failure(request, device, person_id):
    attempts = request.session.get(STATION_PIN_ATTEMPTS_SESSION_KEY, {})
    key = _pin_attempt_key(device, person_id)
    state = attempts.get(key, {"count": 0, "locked_until": 0})
    state["count"] = int(state.get("count") or 0) + 1
    locked = False
    if state["count"] >= STATION_PIN_MAX_ATTEMPTS:
        state["locked_until"] = timezone.now().timestamp() + STATION_PIN_LOCK_SECONDS
        locked = True
    attempts[key] = state
    request.session[STATION_PIN_ATTEMPTS_SESSION_KEY] = attempts
    request.session.modified = True
    return locked


def _clear_pin_failures(request, device, person_id):
    attempts = request.session.get(STATION_PIN_ATTEMPTS_SESSION_KEY, {})
    attempts.pop(_pin_attempt_key(device, person_id), None)
    request.session[STATION_PIN_ATTEMPTS_SESSION_KEY] = attempts
    request.session.modified = True


@login_required
def station_manage(request):
    _require_manage(request.user)
    team = _team(request.user)
    devices = StationDevice.objects.filter(team=team).order_by("name")
    people = Person.objects.filter(team=team, active=True).select_related("station_credential").order_by(
        "last_name", "first_name"
    )
    return render(request, "portal/station/manage.html", {"devices": devices, "people": people})


@login_required
def station_shift_review(request):
    _require_manage(request.user)
    team = _team(request.user)
    all_shifts = list(
        WorkShiftEntry.objects.filter(team=team)
        .select_related("person", "station", "approved_by")
        .order_by("-clock_in")
    )
    recent_shifts = all_shifts[:250]
    attention_shifts = [shift for shift in recent_shifts if not shift.approved_at]
    approved_shifts = [shift for shift in recent_shifts if shift.approved_at]
    totals = defaultdict(
        lambda: {
            "person": None,
            "minutes": 0,
            "approved_minutes": 0,
            "working_student_minutes": 0,
            "shift_count": 0,
        }
    )
    for shift in all_shifts:
        shift.duration_minutes = _shift_minutes(shift)
        shift.duration_display = _format_minutes(shift.duration_minutes)
        row = totals[shift.person_id]
        row["person"] = shift.person
        row["minutes"] += shift.duration_minutes
        if shift.clock_out:
            row["shift_count"] += 1
        if shift.approved_at:
            row["approved_minutes"] += shift.duration_minutes
        if shift.role == WorkShiftEntry.Role.WORKING_STUDENT:
            row["working_student_minutes"] += shift.duration_minutes
    summary = sorted(totals.values(), key=lambda row: (row["person"].last_name, row["person"].first_name))
    for row in summary:
        row["hours_display"] = _format_minutes(row["minutes"])
        row["approved_hours_display"] = _format_minutes(row["approved_minutes"])
        row["working_student_hours_display"] = _format_minutes(row["working_student_minutes"])
    return render(
        request,
        "portal/station/shift_review.html",
        {
            "shifts": recent_shifts,
            "attention_shifts": attention_shifts,
            "approved_shifts": approved_shifts,
            "summary": summary,
        },
    )


@login_required
def station_shift_export(request):
    _require_manage(request.user)
    team = _team(request.user)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="arenaline-staff-hours.csv"'
    writer = csv.writer(response)
    writer.writerow(["Person", "Role", "Clock in", "Clock out", "Minutes", "Hours", "Approved", "Approved by", "Station", "Notes"])
    shifts = WorkShiftEntry.objects.filter(team=team).select_related("person", "station", "approved_by").order_by("person__last_name", "person__first_name", "clock_in")
    for shift in shifts:
        minutes = _shift_minutes(shift)
        writer.writerow([shift.person.display_name, shift.get_role_display(), timezone.localtime(shift.clock_in).strftime("%Y-%m-%d %H:%M"), timezone.localtime(shift.clock_out).strftime("%Y-%m-%d %H:%M") if shift.clock_out else "", minutes, f"{minutes / 60:.2f}", "Yes" if shift.approved_at else "No", shift.approved_by.get_username() if shift.approved_by else "", shift.station.name if shift.station else "", shift.notes])
    _audit_station(team=team, actor=request.user, action="station_shift_exported", entity_type="WorkShiftEntry", entity_label="Staff hours export", summary="Exported ArenaLine Station staff hours", details={"rows": shifts.count()})
    return response


@login_required
def station_shift_edit(request, shift_pk):
    _require_manage(request.user)
    team = _team(request.user)
    shift = get_object_or_404(WorkShiftEntry.objects.select_related("person"), pk=shift_pk, team=team)
    before = {"role": shift.role, "clock_in": shift.clock_in.isoformat(), "clock_out": shift.clock_out.isoformat() if shift.clock_out else None, "notes": shift.notes}
    form = WorkShiftReviewForm(request.POST or None, instance=shift)
    if request.method == "POST" and form.is_valid():
        shift = form.save(commit=False)
        shift.full_clean()
        shift.save()
        after = {"role": shift.role, "clock_in": shift.clock_in.isoformat(), "clock_out": shift.clock_out.isoformat() if shift.clock_out else None, "notes": shift.notes}
        _audit_shift(team, request.user, "station_shift_corrected", shift, {"before": before, "after": after})
        messages.success(request, f"Updated shift for {shift.person.display_name}.")
        return redirect("station_shift_review")
    return render(request, "portal/station/shift_form.html", {"form": form, "shift": shift})


@login_required
def station_shift_approve(request, shift_pk):
    _require_manage(request.user)
    if request.method != "POST":
        raise Http404
    team = _team(request.user)
    shift = get_object_or_404(WorkShiftEntry.objects.select_related("person"), pk=shift_pk, team=team)
    if not shift.clock_out:
        messages.error(request, "Open shifts must be clocked out before approval.")
        return redirect("station_shift_review")
    shift.approved_by = request.user
    shift.approved_at = timezone.now()
    shift.full_clean()
    shift.save(update_fields=["approved_by", "approved_at", "updated_at"])
    _audit_shift(team, request.user, "station_shift_approved", shift, {"approved_at": shift.approved_at.isoformat()})
    messages.success(request, f"Approved shift for {shift.person.display_name}.")
    return redirect("station_shift_review")


@login_required
def station_device_add(request):
    _require_manage(request.user)
    team = _team(request.user)
    form = StationDeviceForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        device = form.save(commit=False)
        device.team = team
        device.device_key = secrets.token_urlsafe(32)
        raw_secret = secrets.token_urlsafe(24)
        device.set_secret(raw_secret)
        device.full_clean()
        device.save()
        _audit_station(team=team, actor=request.user, action="station_device_added", entity_type="StationDevice", entity_id=device.pk, entity_label=device.name, summary=f"Registered Station device — {device.name}", details={"device_key": device.device_key, "active": device.active})
        return render(request, "portal/station/provision.html", {"device": device, "raw_secret": raw_secret})
    return render(request, "portal/station/device_form.html", {"form": form, "title": "Register Station device"})


@login_required
def station_device_edit(request, device_pk):
    _require_manage(request.user)
    team = _team(request.user)
    device = get_object_or_404(StationDevice, pk=device_pk, team=team)
    before = {"name": device.name, "notes": device.notes, "active": device.active}
    form = StationDeviceForm(request.POST or None, instance=device)
    if request.method == "POST" and form.is_valid():
        device = form.save()
        _audit_station(team=team, actor=request.user, action="station_device_updated", entity_type="StationDevice", entity_id=device.pk, entity_label=device.name, summary=f"Updated Station device — {device.name}", details={"before": before, "after": {"name": device.name, "notes": device.notes, "active": device.active}})
        messages.success(request, f"Updated Station device {device.name}.")
        return redirect("station_manage")
    return render(request, "portal/station/device_form.html", {"form": form, "title": "Edit Station device", "device": device})


@login_required
def station_device_rotate_secret(request, device_pk):
    _require_manage(request.user)
    team = _team(request.user)
    device = get_object_or_404(StationDevice, pk=device_pk, team=team)
    if request.method != "POST":
        raise Http404
    raw_secret = secrets.token_urlsafe(24)
    device.set_secret(raw_secret)
    device.save(update_fields=["secret_hash", "updated_at"])
    _audit_station(team=team, actor=request.user, action="station_secret_rotated", entity_type="StationDevice", entity_id=device.pk, entity_label=device.name, summary=f"Rotated Station secret — {device.name}", details={"device_key": device.device_key})
    return render(request, "portal/station/provision.html", {"device": device, "raw_secret": raw_secret, "rotated": True})


@login_required
def station_person_pin(request, person_pk):
    _require_manage(request.user)
    team = _team(request.user)
    person = get_object_or_404(Person, pk=person_pk, team=team, active=True)
    credential = StationCredential.objects.filter(person=person, team=team).first()
    was_active = credential.active if credential else None
    form = StationCredentialForm(request.POST or None, team=team, person=person, initial={"active": credential.active if credential else True})
    if request.method == "POST" and form.is_valid():
        credential = credential or StationCredential(team=team, person=person)
        credential.active = form.cleaned_data["active"]
        credential.set_pin(form.cleaned_data["pin"])
        credential.full_clean()
        credential.save()
        _audit_station(team=team, actor=request.user, action="station_pin_updated", entity_type="StationCredential", entity_id=credential.pk, entity_label=person.display_name, summary=f"Updated Station PIN — {person.display_name}", details={"active_before": was_active, "active_after": credential.active})
        messages.success(request, f"Station PIN updated for {person.display_name}.")
        return redirect("station_manage")
    return render(request, "portal/station/pin_form.html", {"form": form, "person": person, "credential": credential})


def station_activate(request):
    form = StationActivationForm(request.POST or None, initial={"device_key": request.GET.get("device_key", "")})
    if request.method == "POST" and form.is_valid():
        device = StationDevice.objects.filter(device_key=form.cleaned_data["device_key"], active=True).first()
        if device and device.check_secret(form.cleaned_data["secret"]):
            actor = request.user if getattr(request.user, "is_authenticated", False) else None
            _audit_station(team=device.team, actor=actor, action="station_device_activated", entity_type="StationDevice", entity_id=device.pk, entity_label=device.name, summary=f"Activated Station device — {device.name}", details={"device_key": device.device_key})
            request.session[STATION_DEVICE_SESSION_KEY] = device.pk
            _clear_station_person(request)
            if getattr(request.user, "is_authenticated", False):
                logout(request)
            return redirect("station_home")
        messages.error(request, "Station activation failed. Check the device key and secret.")
    return render(request, "portal/station/activate.html", {"form": form})


def station_home(request):
    device = _station_device(request)
    if not device:
        return redirect("station_activate")
    _clear_station_person(request)
    people = Person.objects.filter(team=device.team, active=True, station_credential__active=True).order_by("last_name", "first_name")
    return render(request, "portal/station/home.html", {"device": device, "people": people})


def station_pin(request, person_pk):
    device = _station_device(request)
    if not device:
        return redirect("station_activate")
    person = get_object_or_404(Person, pk=person_pk, team=device.team, active=True, station_credential__active=True)
    lock_remaining = _pin_lock_remaining(request, device, person.pk)
    if lock_remaining:
        return render(request, "portal/station/pin.html", {"device": device, "person": person, "form": StationPinForm(), "locked": True, "lock_remaining": lock_remaining}, status=429)
    form = StationPinForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        credential = person.station_credential
        if credential.check_pin(form.cleaned_data["pin"]):
            _clear_pin_failures(request, device, person.pk)
            request.session[STATION_PERSON_SESSION_KEY] = person.pk
            request.session[STATION_PERSON_AUTH_AT_KEY] = timezone.now().timestamp()
            return redirect("station_action")
        locked = _record_pin_failure(request, device, person.pk)
        messages.error(request, "Too many incorrect PIN attempts. Try again in 5 minutes." if locked else "That PIN did not match. Try again.")
        if locked:
            return render(request, "portal/station/pin.html", {"device": device, "person": person, "form": StationPinForm(), "locked": True, "lock_remaining": STATION_PIN_LOCK_SECONDS}, status=429)
    return render(request, "portal/station/pin.html", {"device": device, "person": person, "form": form})


def station_action(request):
    device = _station_device(request)
    if not device:
        return redirect("station_activate")
    person = _station_person(request, device)
    if not person:
        return redirect("station_home")
    open_shift = WorkShiftEntry.objects.filter(team=device.team, person=person, clock_out__isnull=True).first()
    form = StationClockInForm(request.POST or None, person=person, open_shift=open_shift)
    if request.method == "POST" and form.is_valid():
        if open_shift:
            open_shift.clock_out = timezone.now()
            open_shift.full_clean()
            open_shift.save(update_fields=["clock_out", "updated_at"])
            _audit_shift(device.team, None, "station_clock_out", open_shift, {"clock_out": open_shift.clock_out.isoformat(), "station_id": device.pk})
            _clear_station_person(request)
            return render(request, "portal/station/complete.html", {"device": device, "person": person, "action": "clocked out", "shift": open_shift})
        shift = WorkShiftEntry(team=device.team, person=person, station=device, role=form.cleaned_data["role"], clock_in=timezone.now(), notes=form.cleaned_data.get("notes", ""))
        shift.full_clean()
        shift.save()
        _audit_shift(device.team, None, "station_clock_in", shift, {"clock_in": shift.clock_in.isoformat(), "station_id": device.pk})
        _clear_station_person(request)
        return render(request, "portal/station/complete.html", {"device": device, "person": person, "action": "clocked in", "shift": shift})
    return render(request, "portal/station/action.html", {"device": device, "person": person, "open_shift": open_shift, "form": form})
