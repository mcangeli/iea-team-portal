"""Views for the finance reports domain."""

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


from .finance_reports_helpers import (
    _budget_report_rows,
    _csv_response,
    _finance_report_season,
)

@login_required
def finance_reports(request):
    team = _team(request.user)
    season = _finance_report_season(request, team)
    _require_finance(request.user, season)
    seasons = Season.objects.filter(team=team).order_by("-start_date")
    budget_rows, budget_totals = _budget_report_rows(season)
    receivable_rows, receivable_totals = _receivable_report_rows(season)
    assistance_rows, assistance_totals = _assistance_report_rows(season)
    return render(request, "portal/finance_reports.html", {
        "season": season, "seasons": seasons,
        "budget_line_count": len(budget_rows),
        "budget_totals": budget_totals,
        "receivable_totals": receivable_totals,
        "assistance_totals": assistance_totals,
        "assistance_count": len(assistance_rows),
    })

@login_required
def finance_report_budget(request):
    team = _team(request.user)
    season = _finance_report_season(request, team)
    _require_finance(request.user, season)
    rows, totals = _budget_report_rows(season)
    return render(request, "portal/finance_report_budget.html", {
        "season": season, "seasons": Season.objects.filter(team=team).order_by("-start_date"),
        "rows": rows, "totals": totals,
    })

@login_required
def finance_report_receivables(request):
    team = _team(request.user)
    season = _finance_report_season(request, team)
    _require_finance(request.user, season)
    rows, totals = _receivable_report_rows(season)
    status = request.GET.get("status", "")
    if status in {"overdue", "due_soon", "current", "paid"}:
        rows = [row for row in rows if row["status"] == status]
    return render(request, "portal/finance_report_receivables.html", {
        "season": season, "seasons": Season.objects.filter(team=team).order_by("-start_date"),
        "rows": rows, "totals": totals, "selected_status": status,
    })

@login_required
def finance_report_assistance(request):
    team = _team(request.user)
    season = _finance_report_season(request, team)
    _require_finance(request.user, season)
    rows, totals = _assistance_report_rows(season)
    return render(request, "portal/finance_report_assistance.html", {
        "season": season, "seasons": Season.objects.filter(team=team).order_by("-start_date"),
        "rows": rows, "totals": totals,
    })

@login_required
def finance_report_category(request):
    team = _team(request.user)
    season = _finance_report_season(request, team)
    _require_finance(request.user, season)
    categories = FinancialCategory.objects.filter(team=team).order_by("sort_order", "name")
    category_id = request.GET.get("category")
    kind = request.GET.get("kind", "")
    category = categories.filter(pk=category_id).first() if category_id else None
    tx = FinancialTransaction.objects.filter(team=team, season=season, status=FinancialTransaction.Status.POSTED).select_related("category", "account", "rider", "show")
    if category:
        tx = tx.filter(category=category)
    if kind in {FinancialTransaction.Kind.INCOME, FinancialTransaction.Kind.EXPENSE}:
        tx = tx.filter(kind=kind)
    totals = tx.aggregate(
        income=Sum("amount", filter=Q(kind=FinancialTransaction.Kind.INCOME)),
        expense=Sum("amount", filter=Q(kind=FinancialTransaction.Kind.EXPENSE)),
    )
    income = totals["income"] or Decimal("0")
    expense = totals["expense"] or Decimal("0")
    return render(request, "portal/finance_report_category.html", {
        "season": season, "seasons": Season.objects.filter(team=team).order_by("-start_date"),
        "categories": categories, "selected_category": category, "selected_kind": kind,
        "transactions": tx[:500], "income": income, "expense": expense, "net": income-expense,
    })

@login_required
def finance_report_budget_export(request):
    team = _team(request.user); season = _finance_report_season(request, team)
    _require_finance(request.user, season)
    rows, _ = _budget_report_rows(season)
    return _csv_response(
        f"budget-vs-actual-{season.name if season else 'none'}.csv",
        ["Season","Type","Category","Budget","Actual","Variance","Percent"],
        [[season.name, r["budget"].get_kind_display(), r["budget"].category.name,
          r["budget"].amount, r["actual"], r["variance"],
          f'{r["percent"]:.1f}' if r["percent"] is not None else ""] for r in rows],
    )

@login_required
def finance_report_receivables_export(request):
    team = _team(request.user); season = _finance_report_season(request, team)
    _require_finance(request.user, season)
    rows, _ = _receivable_report_rows(season)
    return _csv_response(
        f"family-receivables-{season.name if season else 'none'}.csv",
        ["Season","Rider","Home Barn","Billed","Credits","Assistance","Payments","Balance","Overdue","Due Soon","Status"],
        [[season.name, r["membership"].rider, r["membership"].home_barn or "", r["billed"], r["credits"],
          r["assistance"], r["payments"], r["balance"], r["overdue"], r["due_soon"], r["status"]] for r in rows],
    )

@login_required
def finance_report_assistance_export(request):
    team = _team(request.user); season = _finance_report_season(request, team)
    _require_finance(request.user, season)
    rows, _ = _assistance_report_rows(season)
    return _csv_response(
        f"financial-assistance-{season.name if season else 'none'}.csv",
        ["Season","Rider","Provider","Program","Award Maximum","Allocated","Submitted","Approved","Reimbursed","Remaining","Status"],
        [[season.name, r["award"].membership.rider, r["award"].provider, r["award"].program_name,
          r["award"].approved_maximum, r["allocated"], r["submitted"], r["approved"],
          r["reimbursed"], r["remaining"], r["award"].get_status_display()] for r in rows],
    )

@login_required
def finance_report_category_export(request):
    team = _team(request.user); season = _finance_report_season(request, team)
    _require_finance(request.user, season)
    category_id = request.GET.get("category")
    kind = request.GET.get("kind", "")
    tx = FinancialTransaction.objects.filter(team=team, season=season, status=FinancialTransaction.Status.POSTED).select_related("category", "account", "rider", "show")
    if category_id:
        tx = tx.filter(category_id=category_id)
    if kind in {FinancialTransaction.Kind.INCOME, FinancialTransaction.Kind.EXPENSE}:
        tx = tx.filter(kind=kind)
    return _csv_response(
        f"category-activity-{season.name if season else 'none'}.csv",
        ["Date","Season","Type","Category","Account","Description","Payee","Rider","Show","Amount","Reference"],
        [[t.transaction_date, t.season.name, t.get_kind_display(), t.category.name, t.account.name,
          t.description, t.payee, t.rider or "", t.show or "", t.amount, t.reference] for t in tx],
    )
