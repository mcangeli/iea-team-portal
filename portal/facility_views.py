from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .facility_forms import FacilityForm, FacilitySpaceForm, HorseStallAssignmentForm
from .model_modules.facilities import Facility, FacilitySpace, HorseStallAssignment
from .platform import can_manage_organization, organization_for_view_user


def _facility_context(user):
    team = organization_for_view_user(user)
    if team is None:
        raise PermissionDenied
    return team


def _require_facility_manager(user):
    if not can_manage_organization(user):
        raise PermissionDenied


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
    spaces = list(facility.spaces.select_related("parent").order_by("name", "id"))
    children_by_parent = {}
    for space in spaces:
        children_by_parent.setdefault(space.parent_id, []).append(space)

    def build_node(space, seen=None):
        seen = set(seen or ())
        if space.pk in seen:
            return {"space": space, "children": []}
        seen.add(space.pk)
        return {
            "space": space,
            "children": [build_node(child, seen) for child in children_by_parent.get(space.pk, [])],
        }

    space_tree = [build_node(space) for space in children_by_parent.get(None, [])]
    current_stall_assignments = (
        HorseStallAssignment.objects.filter(space__facility=facility, end_date__isnull=True)
        .select_related("horse", "space")
        .order_by("space__name", "horse__name")
    )
    current_by_space = {assignment.space_id: assignment for assignment in current_stall_assignments}
    def attach_occupancy(nodes):
        for node in nodes:
            node["stall_assignment"] = current_by_space.get(node["space"].pk)
            attach_occupancy(node["children"])
    attach_occupancy(space_tree)
    return render(request, "portal/facility_detail.html", {
        "facility": facility,
        "spaces": spaces,
        "space_tree": space_tree,
        "current_stall_assignments": current_stall_assignments,
        "can_manage": can_manage_organization(request.user),
    })


@login_required
def facility_create(request):
    _require_facility_manager(request.user)
    team = _facility_context(request.user)
    form = FacilityForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        facility = form.save(commit=False)
        facility.team = team
        facility.save()
        messages.success(request, f"{facility.name} added to Facilities.")
        return redirect("facility_detail", pk=facility.pk)
    return render(request, "portal/facility_form.html", {"form": form, "title": "Add facility"})


@login_required
def facility_edit(request, pk):
    _require_facility_manager(request.user)
    team = _facility_context(request.user)
    facility = get_object_or_404(Facility, pk=pk, team=team)
    form = FacilityForm(request.POST or None, instance=facility)
    if request.method == "POST" and form.is_valid():
        facility = form.save()
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
    assignment = get_object_or_404(
        HorseStallAssignment.objects.select_related("horse", "space__facility"),
        pk=pk, horse__team=team, space__facility__team=team, end_date__isnull=True,
    )
    if request.method == "POST":
        assignment.end_date = timezone.localdate()
        assignment.full_clean()
        assignment.save(update_fields=["end_date", "updated_at"])
        messages.success(request, f"{assignment.horse.display_name} vacated {assignment.space.name}.")
        return redirect("facility_detail", pk=assignment.space.facility_id)
    return render(request, "portal/stall_assignment_vacate.html", {"assignment": assignment})


@login_required
def stall_assignment_move(request, pk):
    _require_facility_manager(request.user)
    team = _facility_context(request.user)
    assignment = get_object_or_404(
        HorseStallAssignment.objects.select_related("horse", "space__facility"),
        pk=pk, horse__team=team, space__facility__team=team, end_date__isnull=True,
    )
    facility = assignment.space.facility
    initial = {"horse": assignment.horse, "start_date": timezone.localdate()}
    form = HorseStallAssignmentForm(request.POST or None, team=team, facility=facility, initial=initial)
    form.fields["horse"].disabled = True
    if request.method == "POST" and form.is_valid():
        move_date = form.cleaned_data["start_date"]
        assignment.end_date = move_date
        assignment.full_clean()
        assignment.save(update_fields=["end_date", "updated_at"])
        new_assignment = form.save(commit=False)
        new_assignment.horse = assignment.horse
        new_assignment.save()
        messages.success(request, f"{assignment.horse.display_name} moved to {new_assignment.space.name}.")
        return redirect("facility_detail", pk=facility.pk)
    return render(request, "portal/stall_assignment_form.html", {
        "form": form, "facility": facility, "assignment": assignment,
        "title": f"Move {assignment.horse.display_name}",
    })
