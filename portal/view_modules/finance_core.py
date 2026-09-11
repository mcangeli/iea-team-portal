"""Views for the finance core domain."""

import re
import csv
from pathlib import Path
from datetime import datetime, time, timedelta
from decimal import Decimal
from functools import wraps
from urllib.parse import urlencode

from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator
from django.http import HttpResponse, FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from ..forms import (
    AnnouncementForm, CalendarEventForm, GuardianContactForm, RiderForm,
    SeasonClassForm, SeasonMembershipForm, ShowClassForm, ShowEntryForm,
    ShowForm, ShowResultForm, SeasonScoringConfigForm, QualificationOverrideForm,
    LessonGroupForm, LessonForm, LessonAttendanceForm, ShowAvailabilityForm,
    VolunteerLogForm, VolunteerReviewForm, VolunteerRequirementForm,
    UserOnboardingForm, UserAccountEditForm, TemporaryPasswordResetForm, NotificationPreferenceForm,
    CommitteeAssignmentForm, ShowLeadAssignmentForm, ShowPlanningItemForm, ShowDayUpdateForm,
    RiderDevelopmentNoteForm, RiderAwardForm, EventRSVPForm, ActionItemForm,
    HistoricalImportUploadForm, HistoricalResultEditForm, HistoricalResultHeaderForm, HistoricalResultFormSet,
    FinancialAccountForm, FinancialCategoryForm, FinancialTransactionForm, SeasonBudgetForm,
    HomeBarnForm, MembershipDuesRateForm, FamilyChargeForm, FamilyCreditForm,
    ServiceAgreementCreditForm, FinancialAssistanceAwardForm, AssistanceClaimForm, FamilyPaymentForm,
    ShowBudgetLineForm, ReimbursementRequestForm, ReimbursementReviewForm, ShowFundingPolicyForm,
    ShowTransactionAllocationForm, FundraisingCampaignForm, FundraisingContributionForm,
    FundraisingPolicyForm,
)
from ..models import (
    Announcement, CalendarEvent, GuardianContact, Rider, RiderGuardian, Season,
    SeasonClass, SeasonMembership, SeasonScoringConfig, QualificationOverride, Show, ShowClass, ShowEntry, ShowResult, UserProfile,
    LessonGroup, Lesson, LessonAttendance, ShowAvailability, ShowDayRiderStatus, VolunteerLog, Notification,
    CommitteeAssignment, ShowLeadAssignment, ShowPlanningItem, ShowDayUpdate, RiderDevelopmentNote, RiderAward,
    EventRSVP, ActionItem, FinancialAccount, FinancialCategory, FinancialTransaction, SeasonBudget,
    HomeBarn, MembershipDuesRate, FamilyCharge, FamilyCredit, ServiceAgreementCredit,
    FinancialAssistanceAward, AssistanceClaim, FamilyPayment, ShowBudgetLine, ReimbursementRequest,
    ShowTransactionAllocation, AuditEvent, FundraisingCampaign, FundraisingContribution,
    FundraisingPolicy,
)

from .common import (
    FINANCE_AUDIT_ENTITY_TYPES,
    HISTORICAL_IMPORT_HEADERS,
    TEAM_LEVELS,
    _active_committee_roles,
    _active_season,
    _announcement_recipients,
    _assistance_report_rows,
    _audit_event,
    _audit_value,
    _can_coordinate_team,
    _can_edit_show_schedule_class,
    _can_finance,
    _can_manage,
    _can_manage_points,
    _can_plan_show,
    _can_view_family_account,
    _can_view_private_rider,
    _ensure_season_open,
    _family_account_totals,
    _finance_season_ids,
    _is_admin,
    _is_non_team_scoring_class,
    _is_rider_account,
    _is_show_lead,
    _personal_riders,
    _planning_item_visible_to_user,
    _qualification_rows,
    _receivable_report_rows,
    _require_finance,
    _require_manage,
    _rider_class_point_rows,
    _selected_team,
    _show_planning_allowed_levels,
    _team,
    _team_scoring_rows,
    _visible_action_items,
    _visible_riders,
    _volunteer_progress_rows,
    _volunteer_requirement,
    friendly_integrity_errors,
)


from .finance_core_helpers import (
    _finance_account_rows,
)

@login_required
def finance_audit_log(request):
    team = _team(request.user)
    season_ids = _finance_season_ids(request.user, team)
    if not season_ids:
        raise PermissionDenied

    finance_entity_types = FINANCE_AUDIT_ENTITY_TYPES
    qs = AuditEvent.objects.filter(team=team, season_id__in=season_ids).select_related("actor", "season")
    is_admin = request.user.is_superuser or (
        hasattr(request.user, "profile") and request.user.profile.role == UserProfile.Role.ADMIN
    )
    if not is_admin:
        qs = qs.filter(entity_type__in=finance_entity_types)

    selected_action = request.GET.get("action", "")
    selected_season = request.GET.get("season", "")
    selected_entity = request.GET.get("entity_type", "")
    entity_id = request.GET.get("entity_id", "")
    q = request.GET.get("q", "").strip()

    valid_actions = {x[0] for x in AuditEvent.Action.choices}
    if selected_action in valid_actions:
        qs = qs.filter(action=selected_action)
    else:
        selected_action = ""
    if selected_season.isdigit() and int(selected_season) in season_ids:
        qs = qs.filter(season_id=int(selected_season))
    else:
        selected_season = ""
    if selected_entity:
        qs = qs.filter(entity_type=selected_entity)
    if entity_id.isdigit():
        qs = qs.filter(entity_id=int(entity_id))
    else:
        entity_id = ""
    if q:
        qs = qs.filter(
            Q(entity_label__icontains=q)
            | Q(summary__icontains=q)
            | Q(actor__first_name__icontains=q)
            | Q(actor__last_name__icontains=q)
            | Q(actor__username__icontains=q)
        )

    paginator = Paginator(qs, 75)
    page = paginator.get_page(request.GET.get("page"))
    params = {
        "action": selected_action, "season": selected_season,
        "entity_type": selected_entity, "entity_id": entity_id, "q": q,
    }
    entity_type_qs = AuditEvent.objects.filter(team=team, season_id__in=season_ids).exclude(entity_type="")
    if not is_admin:
        entity_type_qs = entity_type_qs.filter(entity_type__in=finance_entity_types)
    entity_types = entity_type_qs.values_list("entity_type", flat=True).distinct().order_by("entity_type")
    return render(request, "portal/finance_audit_log.html", {
        "events": page.object_list,
        "page_obj": page,
        "actions": AuditEvent.Action.choices,
        "seasons": Season.objects.filter(team=team, pk__in=season_ids).order_by("-start_date"),
        "entity_types": entity_types,
        "selected_action": selected_action,
        "selected_season": selected_season,
        "selected_entity": selected_entity,
        "entity_id": entity_id,
        "q": q,
        "filter_query": urlencode({k: v for k, v in params.items() if v}),
        "audit_title": "Finance audit log",
        "audit_eyebrow": "AUDIT & CONTROLS",
        "audit_intro": "Immutable activity history for financial and reimbursement workflows.",
        "audit_back_url": "finance_dashboard",
    })

@login_required
def finance_dashboard(request):
    team = _team(request.user)
    season = _active_season(team)
    _require_finance(request.user, season)

    tx = FinancialTransaction.objects.filter(team=team, status=FinancialTransaction.Status.POSTED).select_related(
        "season", "account", "category", "show", "rider", "created_by", "updated_by"
    )
    season_tx = tx.filter(season=season) if season else tx.none()
    totals = season_tx.aggregate(
        income=Sum("amount", filter=Q(kind=FinancialTransaction.Kind.INCOME)),
        expense=Sum("amount", filter=Q(kind=FinancialTransaction.Kind.EXPENSE)),
    )
    income = totals["income"] or Decimal("0")
    expense = totals["expense"] or Decimal("0")
    budget_total = (
        SeasonBudget.objects.filter(season=season).aggregate(total=Sum("amount"))["total"] or Decimal("0")
        if season else Decimal("0")
    )
    receivable_balance = Decimal("0")
    active_award_remaining = Decimal("0")
    if season:
        for membership in SeasonMembership.objects.filter(season=season):
            receivable_balance += _family_account_totals(membership)["balance"]
        for award in FinancialAssistanceAward.objects.filter(membership__season=season, status=FinancialAssistanceAward.Status.ACTIVE):
            active_award_remaining += award.remaining_eligibility

    budget_rows = []
    if season:
        for budget in SeasonBudget.objects.filter(season=season).select_related("category"):
            actual = season_tx.filter(
                category=budget.category, kind=budget.kind
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
            if budget.kind == FinancialTransaction.Kind.INCOME:
                variance = actual - budget.amount
            else:
                variance = budget.amount - actual
            budget_rows.append({"budget": budget, "actual": actual, "variance": variance})

    attention = {
        "overdue_families": 0,
        "overdue_balance": Decimal("0"),
        "draft_claims": 0,
        "outstanding_claims": 0,
        "missing_home_barn": 0,
        "missing_dues_rate": 0,
        "dues_not_generated": 0,
    }
    if season:
        report_rows, report_totals = _receivable_report_rows(season)
        attention["overdue_families"] = sum(1 for r in report_rows if r["overdue"] > 0)
        attention["overdue_balance"] = report_totals.get("overdue", Decimal("0"))
        _, assistance_totals = _assistance_report_rows(season)
        attention["draft_claims"] = assistance_totals.get("draft_claims", 0)
        attention["outstanding_claims"] = assistance_totals.get("outstanding_claims", 0)

        memberships = SeasonMembership.objects.filter(season=season).select_related("home_barn")
        attention["missing_home_barn"] = memberships.filter(home_barn__isnull=True).count()
        rate_barn_ids = set(MembershipDuesRate.objects.filter(season=season).values_list("home_barn_id", flat=True))
        attention["missing_dues_rate"] = sum(
            1 for m in memberships if m.home_barn_id and m.home_barn_id not in rate_barn_ids
        )
        attention["dues_not_generated"] = sum(
            1 for m in memberships
            if not m.family_charges.filter(charge_type=FamilyCharge.ChargeType.MEMBERSHIP_DUES).exists()
        )

    return render(request, "portal/finance_dashboard.html", {
        "season": season,
        "income": income,
        "expense": expense,
        "net": income - expense,
        "budget_total": budget_total,
        "receivable_balance": receivable_balance,
        "active_award_remaining": active_award_remaining,
        "budget_rows": budget_rows,
        "account_rows": _finance_account_rows(team),
        "recent_transactions": tx[:12],
        "attention": attention,
        "can_finance": True,
    })

@login_required
def finance_transaction_list(request):
    team = _team(request.user)
    season = _active_season(team)
    _require_finance(request.user, season)

    tx = FinancialTransaction.objects.filter(team=team).select_related(
        "season", "account", "category", "show", "rider",
        "created_by", "updated_by", "voided_by"
    )

    selected_status = request.GET.get("status", "posted")
    if selected_status == "void":
        tx = tx.filter(status=FinancialTransaction.Status.VOID)
    elif selected_status != "all":
        selected_status = "posted"
        tx = tx.filter(status=FinancialTransaction.Status.POSTED)

    selected_kind = request.GET.get("kind", "")
    if selected_kind in {FinancialTransaction.Kind.INCOME, FinancialTransaction.Kind.EXPENSE}:
        tx = tx.filter(kind=selected_kind)
    else:
        selected_kind = ""

    selected_season = request.GET.get("season", "")
    selected_account = request.GET.get("account", "")
    selected_category = request.GET.get("category", "")
    selected_show = request.GET.get("show", "")
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()
    q = request.GET.get("q", "").strip()

    if selected_season.isdigit():
        tx = tx.filter(season_id=int(selected_season))
    else:
        selected_season = ""
    if selected_account.isdigit():
        tx = tx.filter(account_id=int(selected_account))
    else:
        selected_account = ""
    if selected_category.isdigit():
        tx = tx.filter(category_id=int(selected_category))
    else:
        selected_category = ""
    if selected_show.isdigit():
        tx = tx.filter(show_allocations__show_id=int(selected_show)).distinct()
    else:
        selected_show = ""
    if date_from:
        tx = tx.filter(transaction_date__gte=date_from)
    if date_to:
        tx = tx.filter(transaction_date__lte=date_to)
    if q:
        tx = tx.filter(
            Q(description__icontains=q)
            | Q(payee__icontains=q)
            | Q(reference__icontains=q)
            | Q(category__name__icontains=q)
            | Q(account__name__icontains=q)
            | Q(rider__first_name__icontains=q)
            | Q(rider__last_name__icontains=q)
            | Q(show_allocations__show__name__icontains=q)
        ).distinct()

    paginator = Paginator(tx, 50)
    page = paginator.get_page(request.GET.get("page"))
    filter_params = {
        "status": selected_status,
        "kind": selected_kind,
        "season": selected_season,
        "account": selected_account,
        "category": selected_category,
        "show": selected_show,
        "date_from": date_from,
        "date_to": date_to,
        "q": q,
    }
    filter_query = urlencode({k: v for k, v in filter_params.items() if v})

    return render(request, "portal/finance_transaction_list.html", {
        "transactions": page.object_list,
        "page_obj": page,
        "selected_kind": selected_kind,
        "selected_status": selected_status,
        "selected_season": selected_season,
        "selected_account": selected_account,
        "selected_category": selected_category,
        "selected_show": selected_show,
        "date_from": date_from,
        "date_to": date_to,
        "q": q,
        "filter_query": filter_query,
        "seasons": Season.objects.filter(team=team).order_by("-start_date"),
        "accounts": FinancialAccount.objects.filter(team=team).order_by("name"),
        "categories": FinancialCategory.objects.filter(team=team).order_by("sort_order", "name"),
        "shows": Show.objects.filter(team=team).order_by("-show_date", "name"),
    })

@login_required
@friendly_integrity_errors
def finance_transaction_create(request):
    team = _team(request.user)
    season = _active_season(team)
    _require_finance(request.user, season)
    form = FinancialTransactionForm(request.POST or None, request.FILES or None, team=team)
    if not request.method == "POST" and season:
        form.fields["season"].initial = season
        form.fields["transaction_date"].initial = timezone.localdate()
    if form.is_valid():
        obj = form.save(commit=False)
        obj.team = team
        obj.created_by = request.user
        obj.updated_by = request.user
        obj.full_clean()
        obj.save()
        _audit_event(
            team=team, actor=request.user, action=AuditEvent.Action.CREATED, obj=obj,
            summary=f"Created financial transaction: {obj.description}",
            details={"amount": obj.amount, "kind": obj.kind, "account": obj.account, "category": obj.category},
        )
        messages.success(request, "Financial transaction saved.")
        return redirect("finance_transaction_list")
    return render(request, "portal/form.html", {
        "form": form, "title": "Add transaction", "eyebrow": "TEAM FINANCE"
    })

@login_required
@friendly_integrity_errors
def finance_transaction_edit(request, pk):
    team = _team(request.user)
    obj = get_object_or_404(FinancialTransaction, pk=pk, team=team)
    _require_finance(request.user, obj.season)
    if obj.status == FinancialTransaction.Status.VOID:
        messages.info(request, "Voided transactions are retained for audit history and cannot be edited.")
        return redirect("finance_transaction_list")
    if hasattr(obj, "fundraising_contribution"):
        contribution = obj.fundraising_contribution
        messages.info(
            request,
            "This ledger transaction is controlled by a fundraising contribution. Edit the contribution instead so the ledger and family credit remain synchronized.",
        )
        return redirect("fundraising_contribution_edit", pk=contribution.pk)
    before = {
        "amount": obj.amount, "description": obj.description, "payee": obj.payee,
        "account": obj.account, "category": obj.category, "transaction_date": obj.transaction_date,
    }
    form = FinancialTransactionForm(
        request.POST or None, request.FILES or None, instance=obj, team=team
    )
    if form.is_valid():
        obj = form.save(commit=False)
        obj.team = team
        obj.updated_by = request.user
        obj.full_clean()
        obj.save()
        _audit_event(
            team=team, actor=request.user, action=AuditEvent.Action.UPDATED, obj=obj,
            summary=f"Updated financial transaction: {obj.description}",
            details={
                "before_amount": before["amount"], "after_amount": obj.amount,
                "before_description": before["description"], "after_description": obj.description,
                "before_payee": before["payee"], "after_payee": obj.payee,
                "before_account": before["account"], "after_account": obj.account,
                "before_category": before["category"], "after_category": obj.category,
                "before_date": before["transaction_date"], "after_date": obj.transaction_date,
            },
        )
        messages.success(request, "Financial transaction updated.")
        return redirect("finance_transaction_list")
    return render(request, "portal/form.html", {
        "form": form, "title": "Edit transaction", "eyebrow": "TEAM FINANCE"
    })

@login_required
def finance_transaction_delete(request, pk):
    team = _team(request.user)
    obj = get_object_or_404(FinancialTransaction, pk=pk, team=team)
    _require_finance(request.user, obj.season)
    if obj.status == FinancialTransaction.Status.VOID:
        messages.info(request, "This transaction is already void.")
        return redirect("finance_transaction_list")
    if hasattr(obj, "fundraising_contribution"):
        contribution = obj.fundraising_contribution
        messages.info(
            request,
            "This ledger transaction is controlled by a fundraising contribution. Void the contribution instead so its ledger income and any family credit are corrected together.",
        )
        return redirect("fundraising_contribution_void", pk=contribution.pk)
    if request.method == "POST":
        reason = (request.POST.get("reason") or "Voided by Treasurer").strip()
        create_reversal = request.POST.get("create_reversal") == "1"
        obj.status = FinancialTransaction.Status.VOID
        obj.voided_at = timezone.now()
        obj.voided_by = request.user
        obj.void_reason = reason
        obj.updated_by = request.user
        obj.save(update_fields=["status","voided_at","voided_by","void_reason","updated_by","updated_at"])
        _audit_event(
            team=team, actor=request.user, action=AuditEvent.Action.VOIDED, obj=obj,
            summary=f"Voided financial transaction: {obj.description}",
            details={"amount": obj.amount, "reason": reason, "create_reversal": create_reversal},
        )
        if create_reversal:
            reversal_kind = (
                FinancialTransaction.Kind.EXPENSE
                if obj.kind == FinancialTransaction.Kind.INCOME
                else FinancialTransaction.Kind.INCOME
            )
            reversal = FinancialTransaction(
                team=obj.team, season=obj.season, transaction_date=timezone.localdate(),
                kind=reversal_kind, account=obj.account, category=obj.category, amount=obj.amount,
                payee=obj.payee, description=f"Reversal of: {obj.description}", show=obj.show,
                show_finance_scope=obj.show_finance_scope, rider=obj.rider, reference=obj.reference,
                notes=f"Reversal of transaction #{obj.pk}. {reason}", created_by=request.user,
                updated_by=request.user, reversal_of=obj,
            )
            # A reversal may use the original category even if its directional category normally
            # disallows the opposite kind; preserve audit value without bypassing unrelated validation.
            reversal.save()
            _audit_event(
                team=team, actor=request.user, action=AuditEvent.Action.CREATED, obj=reversal,
                summary=f"Created reversal transaction for #{obj.pk}",
                details={"reversal_of": obj.pk, "amount": reversal.amount, "kind": reversal.kind},
            )
        messages.success(request, "Financial transaction voided; its history has been retained.")
        return redirect("finance_transaction_list")
    return render(request, "portal/finance_transaction_void.html", {
        "object": obj,
        "title": "Void transaction",
    })

@login_required
def finance_transaction_export(request):
    team = _team(request.user)
    season = _active_season(team)
    _require_finance(request.user, season)

    rows = FinancialTransaction.objects.filter(team=team).select_related(
        "season", "account", "category", "show", "rider", "created_by", "updated_by", "voided_by"
    ).order_by("transaction_date", "id")

    selected_status = request.GET.get("status", "posted")
    if selected_status == "void":
        rows = rows.filter(status=FinancialTransaction.Status.VOID)
    elif selected_status != "all":
        rows = rows.filter(status=FinancialTransaction.Status.POSTED)

    selected_kind = request.GET.get("kind", "")
    if selected_kind in {FinancialTransaction.Kind.INCOME, FinancialTransaction.Kind.EXPENSE}:
        rows = rows.filter(kind=selected_kind)

    selected_season = request.GET.get("season", "")
    selected_account = request.GET.get("account", "")
    selected_category = request.GET.get("category", "")
    selected_show = request.GET.get("show", "")
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()
    q = request.GET.get("q", "").strip()

    if selected_season.isdigit():
        rows = rows.filter(season_id=int(selected_season))
    if selected_account.isdigit():
        rows = rows.filter(account_id=int(selected_account))
    if selected_category.isdigit():
        rows = rows.filter(category_id=int(selected_category))
    if selected_show.isdigit():
        rows = rows.filter(show_allocations__show_id=int(selected_show)).distinct()
    if date_from:
        rows = rows.filter(transaction_date__gte=date_from)
    if date_to:
        rows = rows.filter(transaction_date__lte=date_to)
    if q:
        rows = rows.filter(
            Q(description__icontains=q)
            | Q(payee__icontains=q)
            | Q(reference__icontains=q)
            | Q(category__name__icontains=q)
            | Q(account__name__icontains=q)
            | Q(rider__first_name__icontains=q)
            | Q(rider__last_name__icontains=q)
            | Q(show_allocations__show__name__icontains=q)
        ).distinct()

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="team-finance-transactions.csv"'
    writer = csv.writer(response)
    writer.writerow([
        "Date", "Season", "Status", "Type", "Account", "Category", "Amount", "Payee",
        "Description", "Rider", "Reference", "Created by", "Updated by", "Updated at",
        "Voided at", "Voided by", "Void reason",
    ])
    for row in rows:
        writer.writerow([
            row.transaction_date,
            row.season.name,
            row.get_status_display(),
            row.get_kind_display(),
            row.account.name,
            row.category.name,
            row.amount,
            row.payee,
            row.description,
            row.rider or "",
            row.reference,
            row.created_by.get_full_name() or row.created_by.username if row.created_by else "",
            row.updated_by.get_full_name() or row.updated_by.username if row.updated_by else "",
            row.updated_at,
            row.voided_at or "",
            row.voided_by.get_full_name() or row.voided_by.username if row.voided_by else "",
            row.void_reason,
        ])
    return response

@login_required
def finance_accounts(request):
    team = _team(request.user)
    season = _active_season(team)
    _require_finance(request.user, season)
    return render(request, "portal/finance_accounts.html", {
        "account_rows": _finance_account_rows(team),
        "categories": FinancialCategory.objects.filter(team=team),
    })

@login_required
@friendly_integrity_errors
def finance_account_create(request):
    team = _team(request.user)
    season = _active_season(team)
    _require_finance(request.user, season)
    form = FinancialAccountForm(request.POST or None)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.team = team
        obj.save()
        _audit_event(
            team=team, actor=request.user, action=AuditEvent.Action.CREATED, obj=obj,
            season=season, summary=f"Created financial account: {obj.name}",
            details={"active": obj.active},
        )
        messages.success(request, "Financial account added.")
        return redirect("finance_accounts")
    return render(request, "portal/form.html", {
        "form": form, "title": "Add financial account", "eyebrow": "TEAM FINANCE"
    })

@login_required
@friendly_integrity_errors
def finance_account_edit(request, pk):
    team = _team(request.user)
    season = _active_season(team)
    _require_finance(request.user, season)
    obj = get_object_or_404(FinancialAccount, pk=pk, team=team)
    form = FinancialAccountForm(request.POST or None, instance=obj)
    if form.is_valid():
        obj = form.save()
        _audit_event(
            team=team, actor=request.user, action=AuditEvent.Action.UPDATED, obj=obj,
            season=season, summary=f"Updated financial account: {obj.name}",
            details={"active": obj.active},
        )
        messages.success(request, "Financial account updated.")
        return redirect("finance_accounts")
    return render(request, "portal/form.html", {
        "form": form, "title": f"Edit account · {obj.name}", "eyebrow": "TEAM FINANCE"
    })

@login_required
@friendly_integrity_errors
def finance_category_create(request):
    team = _team(request.user)
    season = _active_season(team)
    _require_finance(request.user, season)
    form = FinancialCategoryForm(request.POST or None)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.team = team
        obj.save()
        _audit_event(
            team=team, actor=request.user, action=AuditEvent.Action.CREATED, obj=obj,
            season=season, summary=f"Created financial category: {obj.name}",
            details={"kind": obj.kind, "active": obj.active},
        )
        messages.success(request, "Financial category added.")
        return redirect("finance_accounts")
    return render(request, "portal/form.html", {
        "form": form, "title": "Add financial category", "eyebrow": "TEAM FINANCE"
    })

@login_required
@friendly_integrity_errors
def finance_category_edit(request, pk):
    team = _team(request.user)
    season = _active_season(team)
    _require_finance(request.user, season)
    obj = get_object_or_404(FinancialCategory, pk=pk, team=team)
    form = FinancialCategoryForm(request.POST or None, instance=obj)
    if form.is_valid():
        obj = form.save()
        _audit_event(
            team=team, actor=request.user, action=AuditEvent.Action.UPDATED, obj=obj,
            season=season, summary=f"Updated financial category: {obj.name}",
            details={"kind": obj.kind, "active": obj.active},
        )
        messages.success(request, "Financial category updated.")
        return redirect("finance_accounts")
    return render(request, "portal/form.html", {
        "form": form, "title": f"Edit category · {obj.name}", "eyebrow": "TEAM FINANCE"
    })

@login_required
def finance_budget(request):
    team = _team(request.user)
    season = _active_season(team)
    _require_finance(request.user, season)
    if not season:
        messages.error(request, "Create or activate a season before setting a budget.")
        return redirect("finance_dashboard")
    rows = SeasonBudget.objects.filter(season=season).select_related("category")
    return render(request, "portal/finance_budget.html", {"season": season, "budgets": rows})

@login_required
@friendly_integrity_errors
def finance_budget_create(request):
    team = _team(request.user)
    season = _active_season(team)
    _require_finance(request.user, season)
    if not season:
        messages.error(request, "Create or activate a season before setting a budget.")
        return redirect("finance_dashboard")
    form = SeasonBudgetForm(request.POST or None, season=season, team=team)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.season = season
        obj.updated_by = request.user
        obj.full_clean()
        obj.save()
        _audit_event(
            team=team, actor=request.user, action=AuditEvent.Action.CREATED, obj=obj,
            season=season, summary=f"Created season budget line: {obj.category.name}",
            details={"kind": obj.kind, "amount": obj.amount},
        )
        messages.success(request, "Budget line added.")
        return redirect("finance_budget")
    return render(request, "portal/form.html", {
        "form": form, "title": "Add budget line", "eyebrow": season.name
    })

@login_required
@friendly_integrity_errors
def finance_budget_edit(request, pk):
    team = _team(request.user)
    season = _active_season(team)
    _require_finance(request.user, season)
    obj = get_object_or_404(SeasonBudget.objects.select_related("season", "category"), pk=pk, season__team=team)
    form = SeasonBudgetForm(request.POST or None, instance=obj, season=obj.season, team=team)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.updated_by = request.user
        obj.full_clean()
        obj.save()
        _audit_event(
            team=team, actor=request.user, action=AuditEvent.Action.UPDATED, obj=obj,
            season=obj.season, summary=f"Updated season budget line: {obj.category.name}",
            details={"kind": obj.kind, "amount": obj.amount},
        )
        messages.success(request, "Budget line updated.")
        return redirect("finance_budget")
    return render(request, "portal/form.html", {
        "form": form, "title": f"Edit budget · {obj.category.name}", "eyebrow": obj.season.name
    })

@login_required
def finance_receipt_download(request, pk):
    team = _team(request.user)
    obj = get_object_or_404(FinancialTransaction, pk=pk, team=team)
    _require_finance(request.user, obj.season)
    if not obj.receipt:
        raise Http404("No receipt is attached to this transaction.")
    try:
        handle = obj.receipt.open("rb")
    except FileNotFoundError:
        raise Http404("The receipt file could not be found.")
    filename = obj.receipt.name.rsplit("/", 1)[-1]
    return FileResponse(handle, as_attachment=False, filename=filename)
