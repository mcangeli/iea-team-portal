"""Private helpers for the family finance view domain."""

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


def _model_form_save_cleanly(form, obj, *, save_m2m=False):
    """Run model validation after form cleaning and attach failures to the form instead of raising a 500."""
    try:
        obj.full_clean()
    except ValidationError as exc:
        if hasattr(exc, "message_dict"):
            for field, messages_list in exc.message_dict.items():
                target = field if field in form.fields else None
                for message in messages_list:
                    form.add_error(target, message)
        else:
            form.add_error(None, exc)
        return False
    obj.save()
    if save_m2m:
        form.save_m2m()
    return True

def _sync_assistance_transaction(claim, user):
    """Create/update real team income only after an outside award reimbursement is received."""
    if claim.status != AssistanceClaim.Status.REIMBURSED:
        if claim.financial_transaction_id:
            old_tx = claim.financial_transaction
            if old_tx.status != FinancialTransaction.Status.VOID:
                old_tx.status = FinancialTransaction.Status.VOID
                old_tx.voided_at = timezone.now()
                old_tx.voided_by = user
                old_tx.void_reason = f"Assistance claim #{claim.pk} is no longer reimbursed."
                old_tx.updated_by = user
                old_tx.save(update_fields=[
                    "status", "voided_at", "voided_by", "void_reason", "updated_by", "updated_at"
                ])
            claim.financial_transaction = None
            claim.save(update_fields=["financial_transaction"])
        return
    award = claim.award
    membership = award.membership
    tx = claim.financial_transaction or FinancialTransaction(
        team=membership.season.team,
        season=membership.season,
        created_by=user,
    )
    tx.transaction_date = claim.received_date
    tx.kind = FinancialTransaction.Kind.INCOME
    tx.account = claim.reimbursement_account
    tx.category = claim.reimbursement_category
    tx.amount = claim.reimbursed_amount
    tx.payee = award.provider
    tx.description = f"{award.program_name or award.provider} reimbursement — {membership.rider}"
    tx.rider = membership.rider
    tx.reference = claim.reference
    tx.notes = f"External assistance reimbursement linked to claim #{claim.pk}."
    tx.updated_by = user
    tx.full_clean()
    tx.save()
    if claim.financial_transaction_id != tx.pk:
        claim.financial_transaction = tx
        claim.save(update_fields=["financial_transaction"])

def _sync_family_payment_transaction(payment, user):
    membership = payment.membership
    tx = payment.financial_transaction or FinancialTransaction(
        team=membership.season.team,
        season=membership.season,
        created_by=user,
    )
    tx.transaction_date = payment.received_date
    tx.kind = FinancialTransaction.Kind.INCOME
    tx.account = payment.account
    tx.category = payment.category
    tx.amount = payment.amount
    tx.payee = str(membership.rider)
    tx.description = f"Family payment — {payment.charge.description}"
    tx.rider = membership.rider
    tx.reference = payment.reference
    tx.notes = payment.notes
    tx.updated_by = user
    tx.full_clean()
    tx.save()
    if payment.financial_transaction_id != tx.pk:
        payment.financial_transaction = tx
        payment.save(update_fields=["financial_transaction"])
