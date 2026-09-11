"""Private helpers for the fundraising view domain."""

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


def _sync_fundraising_contribution(contribution, user):
    """Post fundraiser cash once to the ledger and optionally credit a family receivable."""
    campaign = contribution.campaign

    tx = contribution.financial_transaction or FinancialTransaction(
        team=campaign.team,
        season=campaign.season,
        created_by=user,
    )
    tx.transaction_date = contribution.received_date
    tx.kind = FinancialTransaction.Kind.INCOME
    tx.account = contribution.account
    tx.category = contribution.category
    tx.amount = contribution.amount
    tx.payee = contribution.donor_name
    tx.description = f"Fundraiser · {campaign.name}"
    tx.rider = (
        contribution.beneficiary_membership.rider
        if contribution.beneficiary_membership_id else None
    )
    tx.reference = contribution.reference
    tx.notes = contribution.notes
    tx.updated_by = user
    tx.full_clean()
    tx.save()

    if contribution.financial_transaction_id != tx.pk:
        contribution.financial_transaction = tx
        contribution.save(update_fields=["financial_transaction"])

    credit_amount = contribution.family_credit_amount or Decimal("0")
    if credit_amount > 0 and contribution.family_charge_id:
        credit = contribution.family_credit or FamilyCredit(
            created_by=user,
            credit_type=FamilyCredit.CreditType.FUNDRAISING,
        )
        credit.charge = contribution.family_charge
        credit.credit_type = FamilyCredit.CreditType.FUNDRAISING
        credit.amount = credit_amount
        credit.source = campaign.name
        credit.status = FamilyCredit.Status.APPLIED
        detail = f"Fundraising contribution #{contribution.pk}"
        credit.notes = f"{detail}. {contribution.notes}".strip()
        credit.full_clean()
        credit.save()
        if contribution.family_credit_id != credit.pk:
            contribution.family_credit = credit
            contribution.save(update_fields=["family_credit"])
    elif contribution.family_credit_id:
        credit = contribution.family_credit
        credit.status = FamilyCredit.Status.CANCELLED
        credit.notes = (
            f"{credit.notes}\nFamily fundraising credit removed from contribution #{contribution.pk}."
        ).strip()
        credit.save(update_fields=["status", "notes"])

def _fundraising_policy(season):
    if not season:
        return None
    policy, _ = FundraisingPolicy.objects.get_or_create(
        season=season,
        defaults={
            "model": FundraisingPolicy.Model.TEAM_WIDE,
            "default_family_credit_percent": Decimal("0"),
            "participation_optional": True,
        },
    )
    return policy
