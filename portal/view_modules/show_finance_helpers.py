"""Private helpers for the show finance view domain."""

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


def _require_adult_finance_participant(user):
    """Family-facing finance workflows are intentionally unavailable to Rider logins."""
    if _is_rider_account(user):
        raise PermissionDenied

def _show_finance_totals(show):
    allocations = ShowTransactionAllocation.objects.filter(
        show=show,
        transaction__status=FinancialTransaction.Status.POSTED,
    ).select_related("transaction", "transaction__category", "transaction__account", "budget_line")

    income = allocations.filter(
        transaction__kind=FinancialTransaction.Kind.INCOME
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
    expense = allocations.filter(
        transaction__kind=FinancialTransaction.Kind.EXPENSE
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    hosting_income = allocations.filter(
        scope=FinancialTransaction.ShowFinanceScope.HOSTING,
        transaction__kind=FinancialTransaction.Kind.INCOME,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
    hosting_expense = allocations.filter(
        scope=FinancialTransaction.ShowFinanceScope.HOSTING,
        transaction__kind=FinancialTransaction.Kind.EXPENSE,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
    participation_income = allocations.filter(
        scope=FinancialTransaction.ShowFinanceScope.PARTICIPATION,
        transaction__kind=FinancialTransaction.Kind.INCOME,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
    participation_expense = allocations.filter(
        scope=FinancialTransaction.ShowFinanceScope.PARTICIPATION,
        transaction__kind=FinancialTransaction.Kind.EXPENSE,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    legacy_unallocated = FinancialTransaction.objects.filter(
        team=show.team,
        season=show.season,
        show=show,
        status=FinancialTransaction.Status.POSTED,
        show_allocations__isnull=True,
    ).select_related("category", "account")
    legacy_unallocated_amount = legacy_unallocated.aggregate(total=Sum("amount"))["total"] or Decimal("0")

    unassigned_budget_allocations = allocations.filter(budget_line__isnull=True)
    unassigned_budget_amount = unassigned_budget_allocations.aggregate(total=Sum("amount"))["total"] or Decimal("0")

    family_charges = list(show.family_charges.select_related("membership__rider").all())
    billed = sum((c.amount for c in family_charges), Decimal("0"))
    outstanding = sum((c.balance for c in family_charges), Decimal("0"))

    budget_rows = []
    budget_scope_totals = {
        ShowBudgetLine.Scope.HOSTING: {
            "income_planned": Decimal("0"), "income_actual": Decimal("0"),
            "expense_planned": Decimal("0"), "expense_actual": Decimal("0"),
        },
        ShowBudgetLine.Scope.PARTICIPATION: {
            "income_planned": Decimal("0"), "income_actual": Decimal("0"),
            "expense_planned": Decimal("0"), "expense_actual": Decimal("0"),
        },
    }
    for line in show.show_budget_lines.select_related("category"):
        actual = allocations.filter(
            budget_line=line
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
        variance = (
            actual - line.amount
            if line.kind == FinancialTransaction.Kind.INCOME
            else line.amount - actual
        )
        budget_rows.append({"line": line, "actual": actual, "variance": variance})
        bucket = budget_scope_totals[line.scope]
        if line.kind == FinancialTransaction.Kind.INCOME:
            bucket["income_planned"] += line.amount
            bucket["income_actual"] += actual
        else:
            bucket["expense_planned"] += line.amount
            bucket["expense_actual"] += actual

    return {
        "income": income,
        "expense": expense,
        "net": income - expense,
        "hosting_income": hosting_income,
        "hosting_expense": hosting_expense,
        "hosting_net": hosting_income - hosting_expense,
        "participation_income": participation_income,
        "participation_expense": participation_expense,
        "participation_net": participation_income - participation_expense,
        "family_billed": billed,
        "family_outstanding": outstanding,
        "family_charges": family_charges,
        "budget_rows": budget_rows,
        "budget_scope_totals": budget_scope_totals,
        "show_allocations": allocations,
        "unassigned_budget_allocations": unassigned_budget_allocations,
        "unassigned_budget_amount": unassigned_budget_amount,
        "legacy_unallocated_transactions": legacy_unallocated,
        "legacy_unallocated_amount": legacy_unallocated_amount,
    }
