from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .host_show_forms import (
    HostShowOperationsForm,
    HostShowStaffAssignmentForm,
    ShowManagerAssignmentForm,
)
from .host_show_models import HostShowOperations, HostShowStaffAssignment, ShowManagerAssignment
from .models import Show
from .view_modules.common import _can_manage, _is_show_lead, _team


def _host_show(request, show_pk):
    team = _team(request.user)
    show = get_object_or_404(Show, pk=show_pk, team=team)
    if show.financial_role != Show.FinancialRole.HOSTING_ATTENDING:
        raise PermissionDenied("This show is not marked as a hosted show.")
    return show


def _is_show_manager(user, show):
    return ShowManagerAssignment.objects.filter(show=show, user=user, active=True).exists()


def _can_manage_host_show(user, show):
    return _can_manage(user) or _is_show_manager(user, show)


@login_required
def host_show_list(request):
    team = _team(request.user)
    shows = Show.objects.filter(
        team=team,
        financial_role=Show.FinancialRole.HOSTING_ATTENDING,
    ).select_related("season").order_by("show_date", "name")

    can_manage = _can_manage(request.user)
    if not can_manage:
        shows = shows.filter(
            Q(manager_assignments__user=request.user, manager_assignments__active=True)
            | Q(lead_assignments__user=request.user, lead_assignments__active=True)
        ).distinct()

    rows = []
    for show in shows:
        operations = HostShowOperations.objects.filter(show=show).first()
        rows.append({
            "show": show,
            "operations": operations,
            "is_show_manager": _is_show_manager(request.user, show),
        })

    return render(
        request,
        "portal/host_show_list.html",
        {"rows": rows, "can_manage": can_manage},
    )


@login_required
def host_show_workspace(request, show_pk):
    show = _host_show(request, show_pk)
    operations = HostShowOperations.objects.filter(show=show).first()
    can_manage = _can_manage(request.user)
    is_show_manager = _is_show_manager(request.user, show)
    is_show_lead = _is_show_lead(request.user, show)
    if not (can_manage or is_show_manager or is_show_lead):
        raise PermissionDenied

    readiness_items = operations.readiness_items if operations else []
    staff = operations.staff_assignments.filter(active=True) if operations else HostShowStaffAssignment.objects.none()
    managers = show.manager_assignments.filter(active=True).select_related("user")
    return render(
        request,
        "portal/host_show_workspace.html",
        {
            "show": show,
            "operations": operations,
            "readiness_items": readiness_items,
            "staff": staff,
            "managers": managers,
            "can_manage": can_manage,
            "can_manage_host_show": can_manage or is_show_manager,
            "is_show_manager": is_show_manager,
            "is_show_lead": is_show_lead,
        },
    )


@login_required
def host_show_edit(request, show_pk):
    show = _host_show(request, show_pk)
    if not _can_manage_host_show(request.user, show):
        raise PermissionDenied

    operations = HostShowOperations.objects.filter(show=show).first()
    form = HostShowOperationsForm(request.POST or None, instance=operations)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.show = show
        if not obj.pk:
            obj.created_by = request.user
        obj.updated_by = request.user
        obj.save()
        messages.success(request, "Host Show Operations updated.")
        return redirect("host_show_workspace", show_pk=show.pk)

    return render(
        request,
        "portal/host_show_form.html",
        {"show": show, "form": form, "operations": operations},
    )


@login_required
def show_manager_add(request, show_pk):
    show = _host_show(request, show_pk)
    if not _can_manage(request.user):
        raise PermissionDenied
    form = ShowManagerAssignmentForm(request.POST or None, team=show.team, show=show)
    if request.method == "POST" and form.is_valid():
        assignment = form.save(commit=False)
        assignment.show = show
        assignment.save()
        messages.success(request, "Show Manager assigned.")
        return redirect("host_show_workspace", show_pk=show.pk)
    return render(request, "portal/host_show_assignment_form.html", {
        "show": show,
        "form": form,
        "title": "Assign Show Manager",
        "eyebrow": "SHOW HOST LEADERSHIP",
    })


@login_required
@require_POST
def show_manager_remove(request, show_pk, assignment_pk):
    show = _host_show(request, show_pk)
    if not _can_manage(request.user):
        raise PermissionDenied
    assignment = get_object_or_404(ShowManagerAssignment, pk=assignment_pk, show=show)
    assignment.delete()
    messages.success(request, "Show Manager assignment removed.")
    return redirect("host_show_workspace", show_pk=show.pk)


@login_required
def host_staff_add(request, show_pk):
    show = _host_show(request, show_pk)
    if not _can_manage_host_show(request.user, show):
        raise PermissionDenied
    operations, _ = HostShowOperations.objects.get_or_create(
        show=show,
        defaults={"created_by": request.user, "updated_by": request.user},
    )
    form = HostShowStaffAssignmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        staff = form.save(commit=False)
        staff.operations = operations
        staff.save()
        messages.success(request, f"{staff.get_role_display()} added.")
        return redirect("host_show_workspace", show_pk=show.pk)
    return render(request, "portal/host_show_assignment_form.html", {
        "show": show,
        "form": form,
        "title": "Add Show Personnel",
        "eyebrow": "SHOW HOST PERSONNEL",
    })


@login_required
def host_staff_edit(request, show_pk, staff_pk):
    show = _host_show(request, show_pk)
    if not _can_manage_host_show(request.user, show):
        raise PermissionDenied
    staff = get_object_or_404(HostShowStaffAssignment, pk=staff_pk, operations__show=show)
    form = HostShowStaffAssignmentForm(request.POST or None, instance=staff)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Show personnel updated.")
        return redirect("host_show_workspace", show_pk=show.pk)
    return render(request, "portal/host_show_assignment_form.html", {
        "show": show,
        "form": form,
        "title": "Edit Show Personnel",
        "eyebrow": "SHOW HOST PERSONNEL",
    })


@login_required
@require_POST
def host_staff_remove(request, show_pk, staff_pk):
    show = _host_show(request, show_pk)
    if not _can_manage_host_show(request.user, show):
        raise PermissionDenied
    staff = get_object_or_404(HostShowStaffAssignment, pk=staff_pk, operations__show=show)
    staff.delete()
    messages.success(request, "Show personnel removed.")
    return redirect("host_show_workspace", show_pk=show.pk)
