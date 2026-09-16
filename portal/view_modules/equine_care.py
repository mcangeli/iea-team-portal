from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from ..equine_access import require_horse_management
from ..equine_care_forms import HorseCareRecordForm
from ..horse_models import Horse
from ..model_modules.equine_care import HorseCareRecord
from ..models import AuditEvent
from ..platform import organization_for_view_user
from .common import _audit_event


def _horse_for_user(user, pk):
    team = organization_for_view_user(user)
    return get_object_or_404(Horse, pk=pk, team=team)


def _managed_horse(user, pk):
    horse = _horse_for_user(user, pk)
    require_horse_management(user, horse)
    return horse


@login_required
def horse_care_history(request, horse_pk):
    horse = _managed_horse(request.user, horse_pk)
    records = horse.care_records.select_related("provider").order_by("-performed_date", "-id")
    years = list(records.dates("performed_date", "year", order="DESC"))
    selected_year = request.GET.get("year", "").strip()
    if selected_year:
        try:
            selected_year = int(selected_year)
        except ValueError:
            selected_year = None
    else:
        selected_year = None
    if selected_year:
        records = records.filter(performed_date__year=selected_year)
    grouped = []
    current_year = None
    current_records = None
    for record in records:
        year = record.performed_date.year
        if year != current_year:
            current_year = year
            current_records = []
            grouped.append({"year": year, "records": current_records})
        current_records.append(record)
    return render(request, "portal/horse_care_history.html", {
        "horse": horse,
        "year_groups": grouped,
        "years": [value.year for value in years],
        "selected_year": selected_year,
    })


@login_required
def horse_care_add(request, horse_pk):
    horse = _managed_horse(request.user, horse_pk)
    form = HorseCareRecordForm(request.POST or None, team=horse.team, horse=horse)
    if form.is_valid():
        record = form.save(commit=False)
        record.horse = horse
        record.save()
        _audit_event(
            team=horse.team,
            actor=request.user,
            action=AuditEvent.Action.CREATED,
            obj=record,
            summary=f"Added {record.get_care_type_display().lower()} care record for {horse.display_name}",
        )
        messages.success(request, f"Care record added for {horse.display_name}.")
        return redirect("horse_detail", pk=horse.pk)
    return render(request, "portal/horse_care_form.html", {
        "form": form,
        "horse": horse,
        "title": f"Add care record — {horse.display_name}",
    })


@login_required
def horse_care_edit(request, horse_pk, pk):
    horse = _managed_horse(request.user, horse_pk)
    record = get_object_or_404(HorseCareRecord, pk=pk, horse=horse)
    form = HorseCareRecordForm(request.POST or None, instance=record, team=horse.team, horse=horse)
    if form.is_valid():
        record = form.save()
        _audit_event(
            team=horse.team,
            actor=request.user,
            action=AuditEvent.Action.UPDATED,
            obj=record,
            summary=f"Updated care record for {horse.display_name}: {record.title}",
        )
        messages.success(request, "Care record updated.")
        return redirect("horse_detail", pk=horse.pk)
    return render(request, "portal/horse_care_form.html", {
        "form": form,
        "horse": horse,
        "record": record,
        "title": f"Edit care record — {horse.display_name}",
    })
