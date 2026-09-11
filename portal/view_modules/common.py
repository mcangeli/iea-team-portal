"""Cross-domain permissions, shared query helpers, audit utilities, and compatibility helpers."""

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

TEAM_LEVELS = {SeasonMembership.TeamLevel.FUTURES, SeasonMembership.TeamLevel.UPPER}

HISTORICAL_IMPORT_HEADERS = [
    "rider_first_name",
    "rider_last_name",
    "show_name",
    "show_date",
    "competition_level",
    "class_name",
    "competition_track",
    "place",
    "points",
    "horse_name",
    "venue",
    "notes",
    "futures_team_place",
    "upper_team_place",
]

FINANCE_AUDIT_ENTITY_TYPES = {
    "FinancialTransaction", "ShowTransactionAllocation", "ReimbursementRequest",
    "FamilyPayment", "FamilyCharge", "FamilyCredit", "ShowBudgetLine",
    "SeasonBudget", "FinancialAccount", "FinancialCategory",
    "FinancialAssistanceAward", "AssistanceClaim", "ServiceAgreementCredit",
    "FundraisingCampaign", "FundraisingContribution", "FundraisingPolicy",
}

def _audit_value(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    return str(value)

def _audit_event(*, team, actor, action, obj=None, season=None, summary="", details=None,
                 entity_type=None, entity_id=None, entity_label=None):
    """Append a lightweight, immutable operational audit event."""
    if obj is not None:
        entity_type = entity_type or obj.__class__.__name__
        entity_id = entity_id if entity_id is not None else getattr(obj, "pk", None)
        entity_label = entity_label or str(obj)
        if season is None:
            season = getattr(obj, "season", None)
            if season is None and hasattr(obj, "membership"):
                season = getattr(obj.membership, "season", None)
            if season is None and hasattr(obj, "show"):
                season = getattr(obj.show, "season", None)
            if season is None and hasattr(obj, "transaction"):
                season = getattr(obj.transaction, "season", None)
    safe_details = {str(k): _audit_value(v) for k, v in (details or {}).items()}
    return AuditEvent.objects.create(
        team=team,
        season=season,
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        entity_type=entity_type or "Unknown",
        entity_id=entity_id,
        entity_label=(entity_label or entity_type or "Record")[:255],
        summary=(summary or f"{action} {entity_label or entity_type or 'record'}")[:255],
        details=safe_details,
    )

def _finance_season_ids(user, team):
    if _is_rider_account(user):
        return []
    if user.is_superuser or (hasattr(user, "profile") and user.profile.role == UserProfile.Role.ADMIN):
        return list(Season.objects.filter(team=team).values_list("id", flat=True))
    return list(
        CommitteeAssignment.objects.filter(
            user=user, active=True, role=CommitteeAssignment.Role.TREASURER, season__team=team
        ).values_list("season_id", flat=True)
    )

def friendly_integrity_errors(view_func):
    """Turn database constraint collisions in create workflows into a useful UI message."""
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        try:
            with transaction.atomic():
                return view_func(request, *args, **kwargs)
        except IntegrityError:
            if request.method == "POST":
                messages.error(
                    request,
                    "That record could not be added because it conflicts with an existing record. "
                    "Review the existing entries and edit or link the existing record instead."
                )
                return redirect(request.path)
            raise
    return wrapped

def _team(user):
    if user.is_superuser:
        return user.profile.team if hasattr(user, "profile") else None
    if not hasattr(user, "profile") or not user.profile.team:
        raise PermissionDenied("Your account is not assigned to a team.")
    return user.profile.team

def _can_manage(user):
    return user.is_superuser or (
        hasattr(user, "profile") and user.profile.role in [UserProfile.Role.ADMIN, UserProfile.Role.COACH]
    )

def _active_committee_roles(user, season=None):
    qs = CommitteeAssignment.objects.filter(user=user, active=True)
    if season:
        qs = qs.filter(season=season)
    return set(qs.values_list("role", flat=True))

def _can_manage_points(user, season=None):
    return _can_manage(user) or CommitteeAssignment.Role.POINTS_SECRETARY in _active_committee_roles(user, season)

def _is_rider_account(user):
    return bool(
        getattr(user, "is_authenticated", False)
        and hasattr(user, "profile")
        and user.profile.role == UserProfile.Role.RIDER
    )

def _can_finance(user, season=None):
    # Youth Rider accounts never receive Finance access, even if a committee
    # assignment is accidentally attached to the login.
    if _is_rider_account(user):
        return False
    if user.is_superuser:
        return True
    if hasattr(user, "profile") and user.profile.role == UserProfile.Role.ADMIN:
        return True
    return CommitteeAssignment.Role.TREASURER in _active_committee_roles(user, season)

def _require_finance(user, season=None):
    if not _can_finance(user, season):
        raise PermissionDenied

def _can_coordinate_team(user, team_level, season=None):
    if _can_manage(user):
        return True
    roles = _active_committee_roles(user, season)
    return (
        team_level == SeasonMembership.TeamLevel.FUTURES and CommitteeAssignment.Role.FUTURES_PARENT in roles
    ) or (
        team_level == SeasonMembership.TeamLevel.UPPER and CommitteeAssignment.Role.UPPER_PARENT in roles
    )

def _is_show_lead(user, show):
    return ShowLeadAssignment.objects.filter(show=show, user=user, active=True).exists()

def _show_planning_allowed_levels(user, show):
    if _is_rider_account(user):
        return set()
    if _can_manage(user) or _is_show_lead(user, show):
        return {
            ShowPlanningItem.TeamLevel.ALL,
            ShowPlanningItem.TeamLevel.FUTURES,
            ShowPlanningItem.TeamLevel.UPPER,
        }
    roles = _active_committee_roles(user, show.season)
    allowed = set()
    if CommitteeAssignment.Role.FUTURES_PARENT in roles:
        allowed.add(ShowPlanningItem.TeamLevel.FUTURES)
    if CommitteeAssignment.Role.UPPER_PARENT in roles:
        allowed.add(ShowPlanningItem.TeamLevel.UPPER)
    return allowed

def _can_plan_show(user, show):
    return bool(_show_planning_allowed_levels(user, show))

def _planning_item_visible_to_user(user, item):
    if _can_manage(user) or _is_show_lead(user, item.show):
        return True
    if not item.family_visible:
        return False
    if item.team_level == ShowPlanningItem.TeamLevel.ALL:
        return True
    roles = _active_committee_roles(user, item.show.season)
    if (
        item.team_level == ShowPlanningItem.TeamLevel.FUTURES
        and CommitteeAssignment.Role.FUTURES_PARENT in roles
    ):
        return True
    if (
        item.team_level == ShowPlanningItem.TeamLevel.UPPER
        and CommitteeAssignment.Role.UPPER_PARENT in roles
    ):
        return True
    visible_rider_ids = _visible_riders(user, item.show.team).values_list("id", flat=True)
    return SeasonMembership.objects.filter(
        season=item.show.season,
        rider_id__in=visible_rider_ids,
        team_level=item.team_level,
    ).exists()

def _can_edit_show_schedule_class(user, show_class):
    return show_class.team_level in _show_schedule_edit_levels(user, show_class.show)

def _ensure_season_open(season):
    if season and season.is_closed:
        raise PermissionDenied("This season is archived. An Administrator must reopen it before operational records can be changed.")

def _is_admin(user):
    return user.is_superuser or (hasattr(user, "profile") and user.profile.role == UserProfile.Role.ADMIN)

def _require_manage(user):
    if not _can_manage(user):
        raise PermissionDenied

def _personal_riders(user, team):
    """Riders directly linked to the logged-in user as rider or guardian."""
    return team.riders.filter(
        Q(user=user) |
        Q(guardians=user) |
        Q(guardian_links__guardian__user=user)
    ).distinct()

def _visible_riders(user, team):
    """Riders whose private/operational data the user may access."""
    qs = team.riders.all()
    if hasattr(user, "profile") and user.profile.role == UserProfile.Role.PARENT:
        qs = _personal_riders(user, team)
    elif hasattr(user, "profile") and user.profile.role == UserProfile.Role.RIDER:
        qs = qs.filter(user=user)
    return qs

def _can_view_private_rider(user, rider):
    if _can_manage(user):
        return True
    if rider.user_id == user.id:
        return True
    return rider.guardians.filter(pk=user.pk).exists() or rider.guardian_links.filter(guardian__user=user).exists()

def _visible_action_items(user, team):
    qs = ActionItem.objects.filter(team=team).select_related(
        "season", "event", "show", "rider", "assigned_to", "claimed_by"
    )
    if _can_manage(user):
        return qs
    riders = _visible_riders(user, team)
    return qs.filter(family_visible=True).filter(
        Q(rider__in=riders) |
        Q(assigned_to=user) |
        Q(claimed_by=user) |
        Q(rider__isnull=True, assigned_to__isnull=True)
    ).distinct()

def _announcement_recipients(announcement):
    users = User.objects.filter(profile__team=announcement.team, is_active=True).select_related("profile")
    audience = announcement.audience
    if audience == Announcement.Audience.COACHES:
        users = users.filter(profile__role__in=[UserProfile.Role.ADMIN, UserProfile.Role.COACH])
    elif audience == Announcement.Audience.PARENTS:
        users = users.filter(Q(profile__role=UserProfile.Role.PARENT) | Q(guardian_contact__isnull=False)).distinct()
    elif audience == Announcement.Audience.RIDERS:
        users = users.filter(profile__role=UserProfile.Role.RIDER)
    elif audience in {Announcement.Audience.FUTURES, Announcement.Audience.UPPER}:
        season = announcement.season or _active_season(announcement.team)
        if not season:
            return users.none()
        rider_users = Rider.objects.filter(
            team=announcement.team, memberships__season=season, memberships__team_level=audience, user__isnull=False
        ).values_list("user_id", flat=True)
        guardian_users = GuardianContact.objects.filter(
            team=announcement.team, rider_links__rider__memberships__season=season,
            rider_links__rider__memberships__team_level=audience, user__isnull=False
        ).values_list("user_id", flat=True)
        users = users.filter(Q(id__in=rider_users) | Q(id__in=guardian_users) | Q(profile__role__in=[UserProfile.Role.ADMIN, UserProfile.Role.COACH]))
    elif audience == Announcement.Audience.SELECTED:
        users = users.filter(id__in=announcement.selected_users.values("id"))
    return users.distinct()

def _active_season(team):
    return team.seasons.filter(is_active=True).first()

def _selected_team(request):
    value = request.GET.get("team", "all").lower()
    return value if value in TEAM_LEVELS | {"all", "unassigned"} else "all"

def _qualification_rows(season, team_level="all"):
    config, _ = SeasonScoringConfig.objects.get_or_create(season=season)
    memberships = list(
        season.memberships.select_related("rider")
        .prefetch_related("classes", "qualification_overrides")
    )
    if team_level in TEAM_LEVELS:
        memberships = [m for m in memberships if m.team_level == team_level]

    rider_ids = [m.rider_id for m in memberships]
    totals = {}
    if rider_ids:
        grouped = ShowResult.objects.filter(
            entry__rider_id__in=rider_ids,
            entry__show_class__show__season=season,
            entry__show_class__show__competition_level=Show.CompetitionLevel.REGULAR,
            entry__competition_track=ShowEntry.CompetitionTrack.REGULAR,
            entry__show_class__season_class__isnull=False,
            entry__status__in=[ShowEntry.Status.PLANNED, ShowEntry.Status.ENTERED],
        ).values(
            "entry__rider_id",
            "entry__show_class__season_class_id",
        ).annotate(total=Sum("points"))
        totals = {
            (row["entry__rider_id"], row["entry__show_class__season_class_id"]): row["total"] or 0
            for row in grouped
        }

    rows = []
    for membership in memberships:
        override_map = {
            override.season_class_id: override
            for override in membership.qualification_overrides.all()
        }
        for season_class in sorted(
            [sc for sc in membership.classes.all() if sc.active],
            key=lambda sc: (sc.sort_order, sc.name.casefold()),
        ):
            total = totals.get((membership.rider_id, season_class.pk), 0)
            override = override_map.get(season_class.pk)
            auto_qualified = total >= config.individual_qualification_points
            if override and override.status == QualificationOverride.Status.QUALIFIED:
                qualified = True
            elif override and override.status == QualificationOverride.Status.NOT_QUALIFIED:
                qualified = False
            else:
                qualified = auto_qualified
            rows.append({
                "membership": membership,
                "rider": membership.rider,
                "season_class": season_class,
                "points": total,
                "threshold": config.individual_qualification_points,
                "qualified": qualified,
                "override": override,
            })
    return rows

def _team_scoring_rows(season, team_level="all", include_riders=True):
    config, _ = SeasonScoringConfig.objects.get_or_create(season=season)
    levels = [SeasonMembership.TeamLevel.FUTURES, SeasonMembership.TeamLevel.UPPER]
    if team_level in TEAM_LEVELS:
        levels = [team_level]
    rows = []
    totals = {level: 0 for level in levels}
    shows = season.shows.filter(
        competition_level=Show.CompetitionLevel.REGULAR
    ).order_by("show_date", "name")
    for show in shows:
        for level in levels:
            entries = ShowEntry.objects.filter(
                show_class__show=show,
                competition_track=ShowEntry.CompetitionTrack.REGULAR,
                is_point_rider=True,
                status__in=[ShowEntry.Status.PLANNED, ShowEntry.Status.ENTERED],
                rider__memberships__season=season, rider__memberships__team_level=level,
            ).select_related("rider", "show_class__season_class", "result").distinct()
            class_rows = []
            show_total = 0
            for entry in entries:
                if _is_non_team_scoring_class(entry.show_class):
                    continue
                result = entry.result_or_none
                points = result.points if result and result.points is not None else 0
                show_total += points
                class_row = {
                    "class_name": entry.show_class.display_name,
                    "points": points,
                    "result": result,
                }
                if include_riders:
                    class_row["entry"] = entry
                    class_row["rider"] = entry.rider
                class_rows.append(class_row)
            totals[level] += show_total
            rows.append({"show": show, "team_level": level, "team_label": dict(SeasonMembership.TeamLevel.choices)[level], "points": show_total, "classes": class_rows})
    summary = [{
        "team_level": level, "team_label": dict(SeasonMembership.TeamLevel.choices)[level],
        "points": totals[level], "threshold": config.team_qualification_points,
        "qualified": totals[level] >= config.team_qualification_points,
    } for level in levels]
    return rows, summary

def _volunteer_requirement(membership):
    if membership.team_level == SeasonMembership.TeamLevel.FUTURES:
        return membership.season.futures_volunteer_hours_required
    if membership.team_level == SeasonMembership.TeamLevel.UPPER:
        return membership.season.upper_volunteer_hours_required
    return 0

def _volunteer_progress_rows(season, riders):
    memberships = SeasonMembership.objects.filter(season=season, rider__in=riders).select_related("rider", "season").order_by("rider__last_name", "rider__first_name")
    rows = []
    for membership in memberships:
        approved = VolunteerLog.objects.filter(season=season, rider=membership.rider, status=VolunteerLog.Status.APPROVED).aggregate(total=Sum("hours"))["total"] or 0
        pending = VolunteerLog.objects.filter(season=season, rider=membership.rider, status=VolunteerLog.Status.PENDING).aggregate(total=Sum("hours"))["total"] or 0
        required = _volunteer_requirement(membership)
        remaining = max(required - approved, 0)
        rows.append({
            "membership": membership,
            "rider": membership.rider,
            "required": required,
            "approved": approved,
            "pending": pending,
            "remaining": remaining,
            "complete": required <= 0 or approved >= required,
        })
    return rows

def _rider_class_point_rows(season, rider):
    """Return season points per class; individual qualification is never combined across classes."""
    membership = SeasonMembership.objects.filter(
        season=season, rider=rider
    ).prefetch_related("classes").first()
    if not membership:
        return []

    rows = []
    for season_class in membership.classes.all().order_by("sort_order", "name"):
        result_qs = ShowResult.objects.filter(
            entry__rider=rider,
            entry__show_class__show__season=season,
            entry__show_class__show__competition_level=Show.CompetitionLevel.REGULAR,
            entry__competition_track=ShowEntry.CompetitionTrack.REGULAR,
            entry__show_class__season_class=season_class,
            entry__status__in=[ShowEntry.Status.PLANNED, ShowEntry.Status.ENTERED],
        )
        rows.append({
            "season_class": season_class,
            "points": result_qs.aggregate(total=Sum("points"))["total"] or 0,
            "wins": result_qs.filter(place=1).count(),
        })
    return rows

def _is_non_team_scoring_class(show_class):
    """IEA Hunt Seat H8/H14 Walk/Trot classes do not contribute team points."""
    candidates = [
        show_class.class_number or "",
        show_class.display_name or "",
        show_class.name or "",
    ]
    for value in candidates:
        normalized = re.sub(r"[^A-Z0-9]+", "", value.upper())
        if normalized in {"H8", "H14"}:
            return True
        # Handles labels such as "H8 Walk/Trot..." or "H14 - Walk Trot".
        if re.match(r"^\s*H(?:8|14)\b", value.upper()):
            return True
    return False

def _can_view_family_account(user, membership):
    if _is_rider_account(user):
        return False
    if _can_finance(user, membership.season):
        return True
    rider = membership.rider
    return (
        rider.guardians.filter(pk=user.pk).exists()
        or rider.guardian_links.filter(guardian__user=user).exists()
    )

def _family_account_totals(membership):
    charges = list(
        membership.family_charges.select_related("show", "source_dues_rate").prefetch_related(
            "credits", "service_credits", "assistance_claims", "payments"
        )
    )
    billed = sum((c.amount for c in charges if c.status != FamilyCharge.Status.WAIVED), Decimal("0"))
    generic_credits = sum((c.applied_credit_total for c in charges), Decimal("0"))
    service_credits = sum((c.service_credit_total for c in charges), Decimal("0"))
    assistance = sum((c.assistance_total for c in charges), Decimal("0"))
    payments = sum((c.payment_total for c in charges), Decimal("0"))
    balance = sum((c.balance for c in charges), Decimal("0"))
    return {
        "charges": charges,
        "billed": billed,
        "generic_credits": generic_credits,
        "service_credits": service_credits,
        "assistance": assistance,
        "payments": payments,
        "balance": balance,
    }

def _receivable_report_rows(season):
    if not season:
        return [], {}
    today = timezone.localdate()
    rows = []
    totals = {
        "billed": Decimal("0"), "credits": Decimal("0"), "assistance": Decimal("0"),
        "payments": Decimal("0"), "balance": Decimal("0"), "overdue": Decimal("0"),
        "due_soon": Decimal("0"),
    }
    memberships = SeasonMembership.objects.filter(season=season).select_related(
        "rider", "home_barn"
    ).order_by("rider__last_name", "rider__first_name")
    for membership in memberships:
        info = _family_account_totals(membership)
        overdue = due_soon = Decimal("0")
        next_due = None
        for charge in info["charges"]:
            charge_balance = charge.balance
            if charge_balance <= 0 or not charge.due_date:
                continue
            if next_due is None or charge.due_date < next_due:
                next_due = charge.due_date
            if charge.due_date < today:
                overdue += charge_balance
            elif charge.due_date <= today + timedelta(days=14):
                due_soon += charge_balance
        status = "current"
        if overdue > 0:
            status = "overdue"
        elif due_soon > 0:
            status = "due_soon"
        elif info["balance"] <= 0 and info["billed"] > 0:
            status = "paid"
        credits = info["generic_credits"] + info["service_credits"]
        row = {
            "membership": membership, **info, "credits": credits,
            "overdue": overdue, "due_soon": due_soon, "next_due": next_due, "status": status,
        }
        rows.append(row)
        totals["billed"] += info["billed"]
        totals["credits"] += credits
        totals["assistance"] += info["assistance"]
        totals["payments"] += info["payments"]
        totals["balance"] += info["balance"]
        totals["overdue"] += overdue
        totals["due_soon"] += due_soon
    return rows, totals

def _assistance_report_rows(season):
    if not season:
        return [], {}
    rows = []
    totals = {
        "approved_maximum": Decimal("0"), "allocated": Decimal("0"),
        "submitted": Decimal("0"), "approved": Decimal("0"),
        "reimbursed": Decimal("0"), "remaining": Decimal("0"),
        "draft_claims": 0, "outstanding_claims": 0,
    }
    awards = FinancialAssistanceAward.objects.filter(
        membership__season=season
    ).select_related("membership__rider").prefetch_related("claims__charge")
    for award in awards:
        claims = list(award.claims.all())
        submitted = sum(
            (c.amount_requested for c in claims if c.status in {
                AssistanceClaim.Status.SUBMITTED, AssistanceClaim.Status.APPROVED, AssistanceClaim.Status.REIMBURSED
            }), Decimal("0")
        )
        approved = sum(
            (c.amount_approved for c in claims if c.status in {
                AssistanceClaim.Status.APPROVED, AssistanceClaim.Status.REIMBURSED
            }), Decimal("0")
        )
        reimbursed = sum((c.reimbursed_amount for c in claims), Decimal("0"))
        draft_count = sum(1 for c in claims if c.status == AssistanceClaim.Status.DRAFT)
        outstanding_count = sum(1 for c in claims if c.status in {
            AssistanceClaim.Status.SUBMITTED, AssistanceClaim.Status.APPROVED
        })
        allocated = award.allocated_total
        remaining = award.remaining_eligibility
        rows.append({
            "award": award, "claims": claims, "allocated": allocated,
            "submitted": submitted, "approved": approved, "reimbursed": reimbursed,
            "remaining": remaining, "draft_count": draft_count,
            "outstanding_count": outstanding_count,
        })
        totals["approved_maximum"] += award.approved_maximum
        totals["allocated"] += allocated
        totals["submitted"] += submitted
        totals["approved"] += approved
        totals["reimbursed"] += reimbursed
        totals["remaining"] += remaining
        totals["draft_claims"] += draft_count
        totals["outstanding_claims"] += outstanding_count
    return rows, totals

def _show_schedule_edit_levels(user, show):
    """Team levels whose class schedule this user may edit for a show."""
    if _is_rider_account(user):
        return set()
    if (
        _can_manage(user)
        or _is_show_lead(user, show)
        or CommitteeAssignment.Role.POINTS_SECRETARY in _active_committee_roles(user, show.season)
    ):
        return {
            SeasonMembership.TeamLevel.FUTURES,
            SeasonMembership.TeamLevel.UPPER,
            SeasonClass.TeamLevel.BOTH,
        }

    roles = _active_committee_roles(user, show.season)
    levels = set()
    if CommitteeAssignment.Role.FUTURES_PARENT in roles:
        levels.update({SeasonMembership.TeamLevel.FUTURES, SeasonClass.TeamLevel.BOTH})
    if CommitteeAssignment.Role.UPPER_PARENT in roles:
        levels.update({SeasonMembership.TeamLevel.UPPER, SeasonClass.TeamLevel.BOTH})
    return levels
