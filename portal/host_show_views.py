from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .host_show_forms import (
    HostShowOperationsForm,
    HostShowStaffAssignmentForm,
    ShowManagerAssignmentForm,
)
from .host_show_models import HostShowOperations, HostShowStaffAssignment, ShowManagerAssignment
from .models import (
    FinancialTransaction,
    ReimbursementRequest,
    Season,
    Show,
    ShowBudgetLine,
    ShowTransactionAllocation,
)
from .view_modules import dashboards as dashboard_views
from .view_modules.common import _can_finance, _can_manage, _is_show_lead, _team


CLOSED_HOST_SHOW_STATUSES = {Show.Status.COMPLETE, Show.Status.CANCELLED}


def _host_show(request, show_pk):
    team = _team(request.user)
    show = get_object_or_404(Show, pk=show_pk, team=team)
    if show.financial_role != Show.FinancialRole.HOSTING_ATTENDING:
        raise PermissionDenied("This show is not marked as a hosted show.")
    return show


def _is_show_manager(user, show):
    return ShowManagerAssignment.objects.filter(show=show, user=user, active=True).exists()


def _host_show_is_closed(show):
    return show.status in CLOSED_HOST_SHOW_STATUSES


def _can_manage_host_show(user, show):
    # Coach/Admin retain correction authority on archived shows. A Show Manager
    # remains able to review the historical workspace, but normal operational
    # editing ends when the show is explicitly marked Complete or Cancelled.
    return _can_manage(user) or (_is_show_manager(user, show) and not _host_show_is_closed(show))


def _hosting_budget_summary(show):
    lines = list(
        ShowBudgetLine.objects.filter(
            show=show,
            scope=ShowBudgetLine.Scope.HOSTING,
        ).select_related("category")
    )
    planned_expense = sum(
        (line.amount for line in lines if line.kind == FinancialTransaction.Kind.EXPENSE),
        Decimal("0"),
    )
    planned_income = sum(
        (line.amount for line in lines if line.kind == FinancialTransaction.Kind.INCOME),
        Decimal("0"),
    )

    allocations = ShowTransactionAllocation.objects.filter(
        show=show,
        scope=FinancialTransaction.ShowFinanceScope.HOSTING,
        transaction__status=FinancialTransaction.Status.POSTED,
    )
    actual_expense = allocations.filter(
        transaction__kind=FinancialTransaction.Kind.EXPENSE
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
    actual_income = allocations.filter(
        transaction__kind=FinancialTransaction.Kind.INCOME
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    allocation_by_line = {
        row["budget_line_id"]: row["total"] or Decimal("0")
        for row in allocations.exclude(budget_line__isnull=True)
        .values("budget_line_id")
        .annotate(total=Sum("amount"))
    }
    budget_rows = []
    for line in lines:
        actual = allocation_by_line.get(line.pk, Decimal("0"))
        budget_rows.append({
            "line": line,
            "actual": actual,
            "remaining": line.amount - actual,
            "over_budget": actual > line.amount,
        })

    pending_reimbursements = ReimbursementRequest.objects.filter(
        show=show,
        show_finance_scope=FinancialTransaction.ShowFinanceScope.HOSTING,
        status__in=[
            ReimbursementRequest.Status.SUBMITTED,
            ReimbursementRequest.Status.APPROVED,
        ],
    )
    pending_reimbursement_total = pending_reimbursements.aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0")

    return {
        "planned_expense": planned_expense,
        "actual_expense": actual_expense,
        "remaining_expense": planned_expense - actual_expense,
        "planned_income": planned_income,
        "actual_income": actual_income,
        "pending_reimbursement_total": pending_reimbursement_total,
        "pending_reimbursement_count": pending_reimbursements.count(),
        "over_budget": actual_expense > planned_expense,
        "budget_rows": budget_rows,
        "has_budget": bool(lines),
    }


def _host_show_row(show, user):
    operations = HostShowOperations.objects.filter(show=show).first()
    readiness_items = operations.readiness_items if operations else []
    return {
        "show": show,
        "operations": operations,
        "is_show_manager": _is_show_manager(user, show),
        "is_closed": _host_show_is_closed(show),
        "readiness_percent": operations.readiness_percent if operations else 0,
        "missing": [label for label, ready in readiness_items if not ready] if operations else ["Host plan not started"],
        "staff_count": operations.staff_assignments.filter(active=True).count() if operations else 0,
        "budget": _hosting_budget_summary(show),
    }


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

    rows = [_host_show_row(show, request.user) for show in shows]
    active_rows = [row for row in rows if not row["is_closed"]]
    archived_rows = [row for row in rows if row["is_closed"]]

    return render(
        request,
        "portal/host_show_list.html",
        {
            "rows": rows,
            "active_rows": active_rows,
            "archived_rows": archived_rows,
            "can_manage": can_manage,
        },
    )


@login_required
def dashboard_show_manager(request):
    team = _team(request.user)
    can_manage = _can_manage(request.user)
    active_season = Season.objects.filter(team=team, is_active=True).first()

    # Status is the operational boundary. An active-season show remains on the
    # board until it is explicitly marked Complete or Cancelled, even if its
    # calendar date has passed and the team still needs to finish closeout.
    shows = Show.objects.filter(
        team=team,
        financial_role=Show.FinancialRole.HOSTING_ATTENDING,
    ).exclude(status__in=CLOSED_HOST_SHOW_STATUSES)
    if active_season:
        shows = shows.filter(season=active_season)
    shows = shows.select_related("season").order_by("show_date", "name")

    assignment_qs = ShowManagerAssignment.objects.filter(
        show__team=team,
        user=request.user,
        active=True,
    )
    if not can_manage:
        shows = shows.filter(
            manager_assignments__user=request.user,
            manager_assignments__active=True,
        ).distinct()
        if not assignment_qs.exists():
            raise PermissionDenied

    rows = [_host_show_row(show, request.user) for show in shows[:8]]
    historical_assignment_count = assignment_qs.filter(
        show__status__in=CLOSED_HOST_SHOW_STATUSES,
    ).count()

    return render(request, "portal/dashboard_show_manager.html", {
        "rows": rows,
        "next_row": rows[0] if rows else None,
        "can_manage": can_manage,
        "can_finance": _can_finance(request.user, None),
        "workspace_links": dashboard_views._workspace_links(request.user, team, active_season),
        "historical_assignment_count": historical_assignment_count,
    })


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
    is_closed = _host_show_is_closed(show)
    return render(
        request,
        "portal/host_show_workspace.html",
        {
            "show": show,
            "operations": operations,
            "readiness_items": readiness_items,
            "staff": staff,
            "managers": managers,
            "hosting_budget": _hosting_budget_summary(show),
            "can_manage": can_manage,
            "can_manage_host_show": _can_manage_host_show(request.user, show),
            "can_finance_show": _can_finance(request.user, show.season),
            "is_show_manager": is_show_manager,
            "is_show_lead": is_show_lead,
            "is_closed_host_show": is_closed,
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