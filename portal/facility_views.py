from django.contrib import messages
from django.db import models, transaction
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .facility_forms import FacilityForm, FacilitySpaceForm, HorseStallAssignmentForm, HorsePastureAssignmentForm
from .model_modules.facilities import Facility, FacilitySpace, HorseStallAssignment, HorsePastureAssignment
from .platform import can_manage_organization, organization_for_view_user
from .models import AuditEvent
from .view_modules.common import _audit_event


def _facility_context(user):
    team = organization_for_view_user(user)
    if team is None:
        raise PermissionDenied
    return team


def _require_facility_manager(user):
    if not can_manage_organization(user):
        raise PermissionDenied


def _current_assignments(queryset, as_of):
    return queryset.filter(start_date__lte=as_of).filter(
        models.Q(end_date__isnull=True) | models.Q(end_date__gt=as_of)
    )


@login_required
def facility_list(request):
    team = _facility_context(request.user)
    facilities = Facility.objects.filter(team=team).prefetch_related("spaces")
    return render(request, "portal/facility_list.html", {
        "facilities": facilities,
        "can_manage": can_manage_organization(request.user),
    })


@login_required
def facility_detail(request, pk):
    team = _facility_context(request.user)
    facility = get_object_or_404(Facility, pk=pk, team=team)
    top_spaces = list(
        facility.spaces.filter(parent__isnull=True)
        .order_by("space_type", "name", "id")
    )
    all_spaces = list(facility.spaces.all())
    descendant_counts = {}
    for root in top_spaces:
        pending = [root.pk]
        seen = set()
        descendants = []
        while pending:
            parent_id = pending.pop()
            if parent_id in seen:
                continue
            seen.add(parent_id)
            children = [space for space in all_spaces if space.parent_id == parent_id]
            descendants.extend(children)
            pending.extend(child.pk for child in children)
        counts = {}
        for child in descendants:
            label = child.get_space_type_display()
            counts[label] = counts.get(label, 0) + 1
        descendant_counts[root.pk] = counts
    top_space_rows = [
        {"space": space, "counts": descendant_counts.get(space.pk, {})}
        for space in top_spaces
    ]
    return render(request, "portal/facility_detail.html", {
        "facility": facility,
        "top_space_rows": top_space_rows,
        "can_manage": can_manage_organization(request.user),
    })


@login_required
def facility_space_detail(request, pk):
    team = _facility_context(request.user)
    space = get_object_or_404(
        FacilitySpace.objects.select_related("facility", "parent"),
        pk=pk, facility__team=team,
    )
    children = list(space.children.order_by("space_type", "name", "id"))
    groups = []
    group_order = [
        (FacilitySpace.SpaceType.STALL, "Stalls"),
        (FacilitySpace.SpaceType.PASTURE, "Pasture & turnout"),
        (FacilitySpace.SpaceType.STORAGE, "Storage"),
        (FacilitySpace.SpaceType.ARENA, "Rings & arenas"),
    ]
    grouped_ids = set()
    for space_type, label in group_order:
        items = [child for child in children if child.space_type == space_type]
        if items:
            groups.append({"label": label, "spaces": items})
            grouped_ids.update(item.pk for item in items)
    other = [child for child in children if child.pk not in grouped_ids]
    if other:
        groups.append({"label": "Other", "spaces": other})

    today = timezone.localdate()
    current_housing = (
        _current_assignments(HorseStallAssignment.objects.filter(space=space), today)
        .select_related("horse").first()
    )
    current_turnout = (
        _current_assignments(HorsePastureAssignment.objects.filter(space=space), today)
        .select_related("horse").order_by("turnout_type", "horse__name")
    )
    housing_history = (
        HorseStallAssignment.objects.filter(space=space, end_date__lte=today)
        .select_related("horse").order_by("-end_date", "-start_date")[:20]
    )
    turnout_history = (
        HorsePastureAssignment.objects.filter(space=space, end_date__lte=today)
        .select_related("horse").order_by("-end_date", "-start_date")[:20]
    )
    return render(request, "portal/facility_space_detail.html", {
        "facility": space.facility,
        "space": space,
        "groups": groups,
        "current_housing": current_housing,
        "current_turnout": current_turnout,
        "housing_history": housing_history,
        "turnout_history": turnout_history,
        "can_manage": can_manage_organization(request.user),
    })


@login_required
def facility_create(request):
    _require_facility_manager(request.user)
    team = _facility_context(request.user)
    form = FacilityForm(request.POST or None, team=team)
    if request.method == "POST" and form.is_valid():
        facility = form.save(commit=False)
        facility.team = team
        facility.save()
        _audit_event(team=team, actor=request.user, action=AuditEvent.Action.CREATED, obj=facility, summary=f"Created facility {facility.name}")
        messages.success(request, f"{facility.name} added to Facilities.")
        return redirect("facility_detail", pk=facility.pk)
    return render(request, "portal/facility_form.html", {"form": form, "title": "Add facility"})


@login_required
def facility_edit(request, pk):
    _require_facility_manager(request.user)
    team = _facility_context(request.user)
    facility = get_object_or_404(Facility, pk=pk, team=team)
    form = FacilityForm(request.POST or None, instance=facility, team=team)
    if request.method == "POST" and form.is_valid():
        facility = form.save()
        _audit_event(team=team, actor=request.user, action=AuditEvent.Action.UPDATED, obj=facility, summary=f"Updated facility {facility.name}")
        messages.success(request, f"{facility.name} updated.")
        return redirect("facility_detail", pk=facility.pk)
    return render(request, "portal/facility_form.html", {
        "form": form, "facility": facility, "title": f"Edit {facility.name}",
    })


@login_required
def facility_space_create(request, facility_pk):
    _require_facility_manager(request.user)
    team = _facility_context(request.user)
    facility = get_object_or_404(Facility, pk=facility_pk, team=team)
    form = FacilitySpaceForm(request.POST or None, facility=facility)
    if request.method == "POST" and form.is_valid():
        space = form.save()
        _audit_event(team=team, actor=request.user, action=AuditEvent.Action.CREATED, obj=space, summary=f"Created facility space {space.name}")
        messages.success(request, f"{space.name} added to {facility.name}.")
        return redirect("facility_detail", pk=facility.pk)
    return render(request, "portal/facility_space_form.html", {
        "form": form, "facility": facility, "title": f"Add space — {facility.name}",
    })


@login_required
def facility_space_edit(request, pk):
    _require_facility_manager(request.user)
    team = _facility_context(request.user)
    space = get_object_or_404(
        FacilitySpace.objects.select_related("facility"), pk=pk, facility__team=team
    )
    form = FacilitySpaceForm(request.POST or None, instance=space, facility=space.facility)
    if request.method == "POST" and form.is_valid():
        space = form.save()
        _audit_event(team=team, actor=request.user, action=AuditEvent.Action.UPDATED, obj=space, summary=f"Updated facility space {space.name}")
        messages.success(request, f"{space.name} updated.")
        return redirect("facility_detail", pk=space.facility_id)
    return render(request, "portal/facility_space_form.html", {
        "form": form, "facility": space.facility, "space": space,
        "title": f"Edit {space.name}",
    })


@login_required
def stall_assignment_create(request, facility_pk):
    _require_facility_manager(request.user)
    team = _facility_context(request.user)
    facility = get_object_or_404(Facility, pk=facility_pk, team=team)
    form = HorseStallAssignmentForm(request.POST or None, team=team, facility=facility)
    if request.method == "POST" and form.is_valid():
        assignment = form.save()
        _audit_event(team=team, actor=request.user, action=AuditEvent.Action.CREATED, obj=assignment, summary=f"Assigned {assignment.horse.display_name} to {assignment.space.name}")
        messages.success(request, f"{assignment.horse.display_name} assigned to {assignment.space.name}.")
        return redirect("facility_detail", pk=facility.pk)
    return render(request, "portal/stall_assignment_form.html", {
        "form": form, "facility": facility, "title": f"Assign horse housing — {facility.name}",
    })


@login_required
def stall_assignment_edit(request, pk):
    _require_facility_manager(request.user)
    team = _facility_context(request.user)
    assignment = get_object_or_404(
        HorseStallAssignment.objects.select_related("horse", "space__facility"),
        pk=pk, horse__team=team, space__facility__team=team,
    )
    form = HorseStallAssignmentForm(
        request.POST or None, instance=assignment, team=team, facility=assignment.space.facility
    )
    if request.method == "POST" and form.is_valid():
        assignment = form.save()
        _audit_event(team=team, actor=request.user, action=AuditEvent.Action.UPDATED, obj=assignment, summary=f"Updated housing assignment for {assignment.horse.display_name}")
        messages.success(request, f"Housing assignment for {assignment.horse.display_name} updated.")
        return redirect("facility_detail", pk=assignment.space.facility_id)
    return render(request, "portal/stall_assignment_form.html", {
        "form": form, "facility": assignment.space.facility, "assignment": assignment,
        "title": f"Edit housing — {assignment.horse.display_name}",
    })


@login_required
def stall_assignment_vacate(request, pk):
    _require_facility_manager(request.user)
    team = _facility_context(request.user)
    today = timezone.localdate()
    assignment = get_object_or_404(
        _current_assignments(
            HorseStallAssignment.objects.select_related("horse", "space__facility").filter(
                horse__team=team, space__facility__team=team
            ),
            today,
        ),
        pk=pk,
    )
    if request.method == "POST":
        assignment.end_date = today
        assignment.save()
        _audit_event(team=team, actor=request.user, action=AuditEvent.Action.UPDATED, obj=assignment, summary=f"Vacated {assignment.horse.display_name} from {assignment.space.name}", details={"end_date": today})
        messages.success(request, f"{assignment.horse.display_name} vacated {assignment.space.name}.")
        return redirect("facility_detail", pk=assignment.space.facility_id)
    return render(request, "portal/stall_assignment_vacate.html", {"assignment": assignment})


@login_required
def stall_assignment_move(request, pk):
    _require_facility_manager(request.user)
    team = _facility_context(request.user)
    today = timezone.localdate()
    assignment = get_object_or_404(
        _current_assignments(
            HorseStallAssignment.objects.select_related("horse", "space__facility").filter(
                horse__team=team, space__facility__team=team
            ),
            today,
        ),
        pk=pk,
    )
    facility = assignment.space.facility
    initial = {"horse": assignment.horse, "start_date": today}
    form = HorseStallAssignmentForm(
        request.POST or None, team=team, facility=facility, initial=initial, moving_from=assignment
    )
    form.fields["horse"].disabled = True
    if request.method == "POST" and form.is_valid():
        move_date = form.cleaned_data["start_date"]
        with transaction.atomic():
            assignment.end_date = move_date
            assignment.full_clean()
            assignment.save(update_fields=["end_date", "updated_at"])
            new_assignment = form.save(commit=False)
            new_assignment.horse = assignment.horse
            new_assignment.full_clean()
            new_assignment.save()
            _audit_event(team=team, actor=request.user, action=AuditEvent.Action.UPDATED, obj=assignment, summary=f"Ended housing assignment for move of {assignment.horse.display_name}", details={"end_date": move_date})
            _audit_event(team=team, actor=request.user, action=AuditEvent.Action.CREATED, obj=new_assignment, summary=f"Moved {assignment.horse.display_name} to {new_assignment.space.name}", details={"from_space_id": assignment.space_id})
        messages.success(request, f"{assignment.horse.display_name} moved to {new_assignment.space.name}.")
        return redirect("facility_detail", pk=facility.pk)
    return render(request, "portal/stall_assignment_form.html", {
        "form": form, "facility": facility, "assignment": assignment,
        "title": f"Move {assignment.horse.display_name}",
    })


@login_required
def pasture_assignment_create(request, facility_pk):
    _require_facility_manager(request.user)
    team = _facility_context(request.user)
    facility = get_object_or_404(Facility, pk=facility_pk, team=team)
    form = HorsePastureAssignmentForm(request.POST or None, team=team, facility=facility)
    if request.method == "POST" and form.is_valid():
        assignment = form.save()
        _audit_event(team=team, actor=request.user, action=AuditEvent.Action.CREATED, obj=assignment, summary=f"Assigned {assignment.horse.display_name} to {assignment.space.name} for turnout")
        messages.success(request, f"{assignment.horse.display_name} assigned to {assignment.space.name} for turnout.")
        return redirect("facility_detail", pk=facility.pk)
    return render(request, "portal/pasture_assignment_form.html", {
        "form": form, "facility": facility, "title": f"Assign turnout — {facility.name}",
    })


@login_required
def pasture_assignment_edit(request, pk):
    _require_facility_manager(request.user)
    team = _facility_context(request.user)
    assignment = get_object_or_404(
        HorsePastureAssignment.objects.select_related("horse", "space__facility"),
        pk=pk, horse__team=team, space__facility__team=team,
    )
    form = HorsePastureAssignmentForm(
        request.POST or None, instance=assignment, team=team, facility=assignment.space.facility
    )
    if request.method == "POST" and form.is_valid():
        assignment = form.save()
        _audit_event(team=team, actor=request.user, action=AuditEvent.Action.UPDATED, obj=assignment, summary=f"Updated turnout assignment for {assignment.horse.display_name}")
        messages.success(request, f"Turnout assignment for {assignment.horse.display_name} updated.")
        return redirect("facility_detail", pk=assignment.space.facility_id)
    return render(request, "portal/pasture_assignment_form.html", {
        "form": form, "facility": assignment.space.facility, "assignment": assignment,
        "title": f"Edit turnout — {assignment.horse.display_name}",
    })


@login_required
def pasture_assignment_end(request, pk):
    _require_facility_manager(request.user)
    team = _facility_context(request.user)
    assignment = get_object_or_404(
        HorsePastureAssignment.objects.select_related("horse", "space__facility"),
        pk=pk, horse__team=team, space__facility__team=team,
    )
    today = timezone.localdate()
    if assignment.start_date > today or (assignment.end_date is not None and assignment.end_date <= today):
        raise PermissionDenied
    if request.method == "POST":
        assignment.end_date = today
        assignment.save()
        _audit_event(team=team, actor=request.user, action=AuditEvent.Action.UPDATED, obj=assignment, summary=f"Ended turnout for {assignment.horse.display_name} in {assignment.space.name}", details={"end_date": today})
        messages.success(request, f"Turnout ended for {assignment.horse.display_name} in {assignment.space.name}.")
        return redirect("facility_detail", pk=assignment.space.facility_id)
    return render(request, "portal/pasture_assignment_end.html", {"assignment": assignment})


@login_required
def pasture_assignment_move(request, pk):
    _require_facility_manager(request.user)
    team = _facility_context(request.user)
    today = timezone.localdate()
    assignment = get_object_or_404(
        HorsePastureAssignment.objects.select_related("horse", "space__facility"),
        pk=pk, horse__team=team, space__facility__team=team,
        start_date__lte=today,
    )
    if assignment.end_date is not None and assignment.end_date <= today:
        raise PermissionDenied
    facility = assignment.space.facility
    initial = {
        "horse": assignment.horse,
        "turnout_type": assignment.turnout_type,
        "start_date": today,
    }
    form = HorsePastureAssignmentForm(
        request.POST or None, team=team, facility=facility, initial=initial, moving_from=assignment
    )
    form.fields["horse"].disabled = True
    if request.method == "POST" and form.is_valid():
        move_date = form.cleaned_data["start_date"]
        with transaction.atomic():
            assignment.end_date = move_date
            assignment.save()
            new_assignment = form.save(commit=False)
            new_assignment.horse = assignment.horse
            new_assignment.save()
            _audit_event(team=team, actor=request.user, action=AuditEvent.Action.UPDATED, obj=assignment, summary=f"Ended turnout assignment for move of {assignment.horse.display_name}", details={"end_date": move_date})
            _audit_event(team=team, actor=request.user, action=AuditEvent.Action.CREATED, obj=new_assignment, summary=f"Moved {assignment.horse.display_name} turnout to {new_assignment.space.name}", details={"from_space_id": assignment.space_id})
        messages.success(request, f"{assignment.horse.display_name} turnout moved to {new_assignment.space.name}.")
        return redirect("facility_detail", pk=facility.pk)
    return render(request, "portal/pasture_assignment_form.html", {
        "form": form, "facility": facility, "assignment": assignment,
        "title": f"Move turnout — {assignment.horse.display_name}",
    })
