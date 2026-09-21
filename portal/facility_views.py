from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from .facility_forms import FacilityForm, FacilitySpaceForm
from .model_modules.facilities import Facility, FacilitySpace
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
    spaces = facility.spaces.select_related("parent").order_by("parent_id", "name", "id")
    return render(request, "portal/facility_detail.html", {
        "facility": facility,
        "spaces": spaces,
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
