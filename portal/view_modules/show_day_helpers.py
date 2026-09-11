"""Private helpers for the show day view domain."""

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
    _show_schedule_edit_levels,
    _team,
    _team_scoring_rows,
    _visible_action_items,
    _visible_riders,
    _volunteer_progress_rows,
    _volunteer_requirement,
    friendly_integrity_errors,
)


def _show_update_allowed_audiences(user, show):
    """Audiences this user may publish/edit for this show."""
    if _is_rider_account(user):
        return set()
    if _can_manage(user) or _is_show_lead(user, show):
        return {
            ShowDayUpdate.Audience.ALL,
            ShowDayUpdate.Audience.FUTURES,
            ShowDayUpdate.Audience.UPPER,
        }
    roles = _active_committee_roles(user, show.season)
    allowed = set()
    if CommitteeAssignment.Role.FUTURES_PARENT in roles:
        allowed.add(ShowDayUpdate.Audience.FUTURES)
    if CommitteeAssignment.Role.UPPER_PARENT in roles:
        allowed.add(ShowDayUpdate.Audience.UPPER)
    return allowed

def _can_publish_show_update(user, show, audience=None):
    allowed = _show_update_allowed_audiences(user, show)
    return bool(allowed) and (audience is None or audience in allowed)

def _parse_schedule_time(value):
    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%H:%M", "%I:%M %p", "%I:%M%p"):
        try:
            return datetime.strptime(value.upper(), fmt).time()
        except ValueError:
            continue
    raise ValidationError("Enter times like 9:30 AM or 14:30.")

def _shift_schedule_time(value, minutes):
    if value is None:
        return None
    anchor = datetime.combine(timezone.localdate(), value)
    return (anchor + timedelta(minutes=minutes)).time().replace(second=0, microsecond=0)

def _rider_team_level_for_show(rider, show):
    membership = SeasonMembership.objects.filter(rider=rider, season=show.season).first()
    return membership.team_level if membership else None

def _can_update_show_day_rider_status(user, show, rider):
    if _is_rider_account(user):
        return rider.user_id == user.id
    if _can_manage(user) or _is_show_lead(user, show):
        return True

    team_level = _rider_team_level_for_show(rider, show)
    roles = _active_committee_roles(user, show.season)

    if (
        team_level == SeasonMembership.TeamLevel.FUTURES
        and CommitteeAssignment.Role.FUTURES_PARENT in roles
    ):
        return True
    if (
        team_level == SeasonMembership.TeamLevel.UPPER
        and CommitteeAssignment.Role.UPPER_PARENT in roles
    ):
        return True

    # Ordinary parents/guardians can update only their own rider.
    return (
        rider.guardians.filter(pk=user.pk).exists()
        or rider.guardian_links.filter(guardian__user=user).exists()
    )

def _show_day_operational_user(user, show):
    if _is_rider_account(user):
        return False
    roles = _active_committee_roles(user, show.season)
    return bool(
        _can_manage(user)
        or _is_show_lead(user, show)
        or CommitteeAssignment.Role.FUTURES_PARENT in roles
        or CommitteeAssignment.Role.UPPER_PARENT in roles
        or CommitteeAssignment.Role.POINTS_SECRETARY in roles
    )

def _show_day_operational_levels(user, show):
    """Return None for full-team operations, or the team levels the user may operate."""
    if _is_rider_account(user):
        return set()
    roles = _active_committee_roles(user, show.season)
    if (
        _can_manage(user)
        or _is_show_lead(user, show)
        or CommitteeAssignment.Role.POINTS_SECRETARY in roles
    ):
        return None

    levels = set()
    if CommitteeAssignment.Role.FUTURES_PARENT in roles:
        levels.add(SeasonMembership.TeamLevel.FUTURES)
    if CommitteeAssignment.Role.UPPER_PARENT in roles:
        levels.add(SeasonMembership.TeamLevel.UPPER)
    return levels

def _show_day_participating_riders(show):
    return (
        Rider.objects.filter(
            show_entries__show_class__show=show,
            show_entries__status__in=[ShowEntry.Status.PLANNED, ShowEntry.Status.ENTERED],
        )
        .distinct()
        .order_by("last_name", "first_name")
    )

def _visible_show_day_updates(user, show):
    updates = show.day_updates.filter(published=True).select_related("created_by", "updated_by")
    if _can_manage(user) or _is_show_lead(user, show):
        return updates
    visible_ids = []
    for update in updates:
        if _show_update_recipients(update).filter(pk=user.pk).exists():
            visible_ids.append(update.pk)
    return updates.filter(pk__in=visible_ids)

def _show_update_family_user_ids(show, audience):
    entries = ShowEntry.objects.filter(show_class__show=show).exclude(status=ShowEntry.Status.SCRATCHED)
    if audience in {ShowDayUpdate.Audience.FUTURES, ShowDayUpdate.Audience.UPPER}:
        entries = entries.filter(
            rider__memberships__season=show.season,
            rider__memberships__team_level=audience,
        )
    rider_ids = entries.values_list("rider_id", flat=True).distinct()
    rider_user_ids = Rider.objects.filter(pk__in=rider_ids, user__isnull=False).values_list("user_id", flat=True)
    guardian_contact_ids = GuardianContact.objects.filter(
        rider_links__rider_id__in=rider_ids, user__isnull=False
    ).values_list("user_id", flat=True)
    legacy_guardian_ids = User.objects.filter(guardian_riders__id__in=rider_ids).values_list("id", flat=True)
    return set(rider_user_ids) | set(guardian_contact_ids) | set(legacy_guardian_ids)

def _show_update_recipients(update):
    show = update.show
    ids = _show_update_family_user_ids(show, update.audience)

    # Coaches/Admins and assigned Show Leads always receive show-day updates.
    ids.update(User.objects.filter(
        profile__team=show.team,
        profile__role__in=[UserProfile.Role.ADMIN, UserProfile.Role.COACH],
        is_active=True,
    ).values_list("id", flat=True))
    ids.update(ShowLeadAssignment.objects.filter(
        show=show, active=True, user__is_active=True
    ).values_list("user_id", flat=True))

    # The Secretary needs show-day context for results entry.
    ids.update(CommitteeAssignment.objects.filter(
        season=show.season, active=True,
        role=CommitteeAssignment.Role.POINTS_SECRETARY,
        user__is_active=True,
    ).values_list("user_id", flat=True))

    # Team Parent updates stay aligned to the parent's team designation.
    parent_roles = []
    if update.audience == ShowDayUpdate.Audience.FUTURES:
        parent_roles = [CommitteeAssignment.Role.FUTURES_PARENT]
    elif update.audience == ShowDayUpdate.Audience.UPPER:
        parent_roles = [CommitteeAssignment.Role.UPPER_PARENT]
    else:
        parent_roles = [CommitteeAssignment.Role.FUTURES_PARENT, CommitteeAssignment.Role.UPPER_PARENT]
    ids.update(CommitteeAssignment.objects.filter(
        season=show.season, active=True, role__in=parent_roles, user__is_active=True
    ).values_list("user_id", flat=True))

    return User.objects.filter(pk__in=ids, is_active=True).select_related("profile").distinct()

def _deliver_show_update(update, *, revised=False):
    recipients = list(_show_update_recipients(update))
    title = f"Updated: {update.title}" if revised else update.title
    link = f"/shows/{update.show_id}/updates/"
    Notification.objects.bulk_create([
        Notification(
            user=user,
            show_day_update=update,
            title=title,
            body=update.body,
            link=link,
        )
        for user in recipients
    ])
    if update.send_email and settings.EMAIL_HOST:
        subject_prefix = update.show.team.short_name or update.show.team.name
        for user in recipients:
            profile = getattr(user, "profile", None)
            if not user.email or (profile and not profile.email_show_updates):
                continue
            send_mail(
                subject=f"{subject_prefix}: {title}",
                message=f"{update.show.name}\n\n{update.body}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
    return len(recipients)
