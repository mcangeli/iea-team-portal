import secrets

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from portal.model_modules.station import StationCredential, StationDevice, WorkShiftEntry
from portal.model_modules.people import Person
from portal.station_forms import (
    StationActivationForm,
    StationClockInForm,
    StationCredentialForm,
    StationDeviceForm,
    StationPinForm,
)
from portal.view_modules.common import _require_manage, _team


STATION_DEVICE_SESSION_KEY = "arenaline_station_device_id"
STATION_PERSON_SESSION_KEY = "arenaline_station_person_id"
STATION_PERSON_AUTH_AT_KEY = "arenaline_station_person_auth_at"
STATION_PERSON_AUTH_SECONDS = 120


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


@login_required
def station_manage(request):
    _require_manage(request.user)
    team = _team(request.user)
    devices = StationDevice.objects.filter(team=team).order_by("name")
    people = Person.objects.filter(team=team, active=True).select_related("station_credential").order_by(
        "last_name", "first_name"
    )
    return render(
        request,
        "portal/station/manage.html",
        {"devices": devices, "people": people},
    )


@login_required
def station_device_add(request):
    _require_manage(request.user)
    team = _team(request.user)
    form = StationDeviceForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        device = form.save(commit=False)
        device.team = team
        raw_secret = secrets.token_urlsafe(24)
        device.set_secret(raw_secret)
        device.full_clean()
        device.save()
        return render(
            request,
            "portal/station/provision.html",
            {"device": device, "raw_secret": raw_secret},
        )
    return render(request, "portal/station/device_form.html", {"form": form, "title": "Register Station device"})


@login_required
def station_device_edit(request, device_pk):
    _require_manage(request.user)
    team = _team(request.user)
    device = get_object_or_404(StationDevice, pk=device_pk, team=team)
    form = StationDeviceForm(request.POST or None, instance=device)
    if request.method == "POST" and form.is_valid():
        form.save()
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
    return render(
        request,
        "portal/station/provision.html",
        {"device": device, "raw_secret": raw_secret, "rotated": True},
    )


@login_required
def station_person_pin(request, person_pk):
    _require_manage(request.user)
    team = _team(request.user)
    person = get_object_or_404(Person, pk=person_pk, team=team, active=True)
    credential = StationCredential.objects.filter(person=person, team=team).first()
    form = StationCredentialForm(
        request.POST or None,
        team=team,
        person=person,
        initial={"active": credential.active if credential else True},
    )
    if request.method == "POST" and form.is_valid():
        credential = credential or StationCredential(team=team, person=person)
        credential.active = form.cleaned_data["active"]
        credential.set_pin(form.cleaned_data["pin"])
        credential.full_clean()
        credential.save()
        messages.success(request, f"Station PIN updated for {person.display_name}.")
        return redirect("station_manage")
    return render(
        request,
        "portal/station/pin_form.html",
        {"form": form, "person": person, "credential": credential},
    )


def station_activate(request):
    form = StationActivationForm(request.POST or None, initial={"device_key": request.GET.get("device_key", "")})
    if request.method == "POST" and form.is_valid():
        device = StationDevice.objects.filter(device_key=form.cleaned_data["device_key"], active=True).first()
        if device and device.check_secret(form.cleaned_data["secret"]):
            request.session[STATION_DEVICE_SESSION_KEY] = device.pk
            _clear_station_person(request)
            StationDevice.objects.filter(pk=device.pk).update(last_seen_at=timezone.now())
            return redirect("station_home")
        form.add_error(None, "That Station device key and secret could not be verified.")
    return render(request, "portal/station/activate.html", {"form": form})


def station_deactivate(request):
    request.session.pop(STATION_DEVICE_SESSION_KEY, None)
    _clear_station_person(request)
    return redirect("station_activate")


def station_home(request):
    device = _station_device(request)
    if not device:
        return redirect("station_activate")
    _clear_station_person(request)
    credentials = (
        StationCredential.objects.filter(team=device.team, active=True, person__active=True)
        .select_related("person")
        .order_by("person__last_name", "person__first_name")
    )
    return render(request, "portal/station/home.html", {"device": device, "credentials": credentials})


def station_identify(request, person_pk):
    device = _station_device(request)
    if not device:
        return redirect("station_activate")
    credential = get_object_or_404(
        StationCredential.objects.select_related("person"),
        team=device.team,
        person_id=person_pk,
        active=True,
        person__active=True,
    )
    form = StationPinForm(request.POST or None, initial={"person_id": credential.person_id})
    if request.method == "POST" and form.is_valid():
        if form.cleaned_data["person_id"] != credential.person_id:
            raise Http404
        if credential.check_pin(form.cleaned_data["pin"]):
            StationCredential.objects.filter(pk=credential.pk).update(last_used_at=timezone.now())
            request.session[STATION_PERSON_SESSION_KEY] = credential.person_id
            request.session[STATION_PERSON_AUTH_AT_KEY] = timezone.now().timestamp()
            return redirect("station_action")
        form.add_error("pin", "That PIN is not correct.")
    return render(
        request,
        "portal/station/identify.html",
        {"device": device, "person": credential.person, "form": form},
    )


def station_action(request):
    device = _station_device(request)
    if not device:
        return redirect("station_activate")
    person = _station_person(request, device)
    if not person:
        return redirect("station_home")

    open_shift = WorkShiftEntry.objects.filter(team=device.team, person=person, clock_out__isnull=True).first()
    form = StationClockInForm(request.POST or None, person=person)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "clock_out" and open_shift:
            open_shift.clock_out = timezone.now()
            open_shift.full_clean()
            open_shift.save(update_fields=["clock_out", "updated_at"])
            _clear_station_person(request)
            return render(
                request,
                "portal/station/complete.html",
                {"device": device, "person": person, "message": "You are clocked out."},
            )
        if action == "clock_in" and not open_shift and form.is_valid():
            shift = WorkShiftEntry(
                team=device.team,
                person=person,
                station=device,
                role=form.cleaned_data["role"],
                clock_in=timezone.now(),
            )
            shift.full_clean()
            shift.save()
            _clear_station_person(request)
            return render(
                request,
                "portal/station/complete.html",
                {"device": device, "person": person, "message": "You are clocked in."},
            )

    return render(
        request,
        "portal/station/action.html",
        {"device": device, "person": person, "open_shift": open_shift, "form": form},
    )
