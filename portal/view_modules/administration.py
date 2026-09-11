"""Views for the administration domain."""

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


from .administration_helpers import (
    _can_manage_user,
)

@login_required
def committee_list(request):
    team = _team(request.user)
    season = _active_season(team)
    assignments = CommitteeAssignment.objects.filter(team=team, season=season).select_related("user") if season else []
    return render(request, "portal/committee_list.html", {
        "season": season, "assignments": assignments, "can_manage": _can_manage(request.user)
    })

@login_required
@friendly_integrity_errors
def committee_assignment_create(request):
    _require_manage(request.user)
    team = _team(request.user); season = _active_season(team)
    if not season:
        messages.error(request, "Create or activate a season before assigning committee chairs.")
        return redirect("committee_list")
    form = CommitteeAssignmentForm(request.POST or None, team=team, season=season)
    if form.is_valid():
        obj = form.save(commit=False); obj.team = team; obj.season = season; obj.save()
        _audit_event(
            team=team, actor=request.user, action=AuditEvent.Action.CREATED, obj=obj, season=season,
            summary=f"Created committee assignment: {obj}",
            details={"role": obj.role, "user": obj.user, "active": obj.active},
        )
        messages.success(request, "Committee assignment saved.")
        return redirect("committee_list")
    return render(request, "portal/form.html", {"form": form, "title": "Assign committee chair", "eyebrow": "COMMITTEES"})

@login_required
def committee_assignment_edit(request, pk):
    _require_manage(request.user)
    team = _team(request.user)
    obj = get_object_or_404(CommitteeAssignment.objects.select_related("season"), pk=pk, team=team)
    _ensure_season_open(obj.season)
    form = CommitteeAssignmentForm(request.POST or None, instance=obj, team=team)
    if form.is_valid():
        obj = form.save()
        _audit_event(
            team=team, actor=request.user, action=AuditEvent.Action.UPDATED, obj=obj, season=obj.season,
            summary=f"Updated committee assignment: {obj}",
            details={"role": obj.role, "user": obj.user, "active": obj.active},
        )
        messages.success(request, "Committee assignment updated.")
        return redirect("committee_list")
    return render(request, "portal/form.html", {"form": form, "title": "Edit committee assignment", "eyebrow": "COMMITTEES"})

@login_required
def user_list(request):
    _require_manage(request.user)
    team = _team(request.user)
    users = User.objects.filter(profile__team=team).select_related("profile", "rider_record", "guardian_contact").order_by("last_name", "first_name", "username")
    if not _is_admin(request.user):
        users = users.filter(profile__role__in=[UserProfile.Role.PARENT, UserProfile.Role.RIDER])
    return render(request, "portal/user_list.html", {"users": users, "is_admin_actor": _is_admin(request.user)})

@login_required
def user_create(request, rider_pk=None, guardian_pk=None):
    _require_manage(request.user)
    team = _team(request.user)
    rider = get_object_or_404(Rider, pk=rider_pk, team=team, user__isnull=True) if rider_pk else None
    guardian = get_object_or_404(GuardianContact, pk=guardian_pk, team=team, user__isnull=True) if guardian_pk else None
    form = UserOnboardingForm(request.POST or None, team=team, actor=request.user, initial_rider=rider, initial_guardian=guardian)
    if form.is_valid():
        try:
            user = form.save()
        except ValidationError as exc:
            form.add_error(None, exc)
        except IntegrityError as exc:
            # A double-click or browser retry can submit onboarding twice before
            # the first transaction becomes visible to the second request.
            # After the failed transaction rolls back, reconcile against the
            # account that may just have been created by the first request.
            username = form.cleaned_data.get("username", "").strip()
            existing = User.objects.filter(username__iexact=username).first()
            selected_rider = form.cleaned_data.get("rider")
            selected_guardian = form.cleaned_data.get("guardian")
            completed_by_first_request = False

            if existing:
                rider_ok = True
                guardian_ok = True
                if selected_rider:
                    selected_rider.refresh_from_db(fields=["user"])
                    rider_ok = selected_rider.user_id == existing.id
                if selected_guardian:
                    selected_guardian.refresh_from_db(fields=["user"])
                    guardian_ok = selected_guardian.user_id == existing.id
                completed_by_first_request = rider_ok and guardian_ok

            if completed_by_first_request:
                messages.success(
                    request,
                    f"Login created for {existing.get_full_name() or existing.username}. "
                    "They must change the temporary password at first login."
                )
                return redirect("user_list")

            cause = getattr(exc, "__cause__", None)
            diag = getattr(cause, "diag", None)
            constraint = getattr(diag, "constraint_name", None)
            friendly = {
                "auth_user_username_key": "That username is already in use. Choose a different username.",
                "auth_user_pkey": "The database user ID sequence is out of sync. Upgrade to the latest portal release to repair the sequence, then try again.",
                "portal_userprofile_pkey": "The user-profile ID sequence is out of sync. Upgrade to the latest portal release to repair the sequence, then try again.",
                "portal_userprofile_user_id_key": "A profile already exists for this login.",
                "portal_rider_user_id_key": "That login is already attached to another rider.",
                "portal_guardiancontact_user_id_key": "That login is already attached to another parent/guardian.",
            }
            message = friendly.get(
                constraint,
                "That login could not be created because of a database constraint conflict."
            )
            if constraint and constraint not in friendly:
                message += f" Constraint: {constraint}."
            form.add_error(None, message)
        else:
            messages.success(request, f"Login created for {user.get_full_name() or user.username}. They must change the temporary password at first login.")
            return redirect("user_list")
    return render(request, "portal/user_form.html", {"form": form, "title": "Add user", "eyebrow": "USER ONBOARDING", "default_password_configured": bool(settings.DEFAULT_TEMP_PASSWORD)})

@login_required
def user_edit(request, pk):
    _require_manage(request.user)
    team = _team(request.user)
    target = get_object_or_404(User.objects.select_related("profile"), pk=pk, profile__team=team)
    if not _can_manage_user(request.user, target):
        raise PermissionDenied
    form = UserAccountEditForm(request.POST or None, team=team, actor=request.user, user_obj=target)
    if form.is_valid():
        form.save()
        target.refresh_from_db()
        _audit_event(
            team=team, actor=request.user, action=AuditEvent.Action.UPDATED,
            season=_active_season(team), entity_type="User", entity_id=target.pk,
            entity_label=target.get_full_name() or target.username,
            summary=f"Updated user account: {target.get_full_name() or target.username}",
            details={"role": getattr(target.profile, "role", ""), "active": target.is_active},
        )
        messages.success(request, "User account and links updated.")
        return redirect("user_list")
    return render(request, "portal/user_form.html", {"form": form, "title": f"Manage {target.get_full_name() or target.username}", "eyebrow": "USERS", "target_user": target})

@login_required
def user_reset_password(request, pk):
    _require_manage(request.user)
    team = _team(request.user)
    target = get_object_or_404(User.objects.select_related("profile"), pk=pk, profile__team=team)
    if not _can_manage_user(request.user, target):
        raise PermissionDenied
    if target == request.user:
        messages.error(request, "Use Change password for your own account."); return redirect("user_list")
    form = TemporaryPasswordResetForm(request.POST or None, user_obj=target)
    if request.method == "POST" and form.is_valid():
        target.set_password(form.cleaned_data["resolved_password"]); target.save(update_fields=["password"])
        target.profile.must_change_password = True; target.profile.save(update_fields=["must_change_password"])
        messages.success(request, f"Temporary password reset for {target.get_full_name() or target.username}. A password change will be required at next login.")
        return redirect("user_list")
    return render(request, "portal/user_form.html", {"form": form, "title": "Reset temporary password", "eyebrow": target.username, "default_password_configured": bool(settings.DEFAULT_TEMP_PASSWORD)})

@login_required
def password_change_required(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save(); update_session_auth_hash(request, user)
        if hasattr(user, "profile"):
            user.profile.must_change_password = False; user.profile.save(update_fields=["must_change_password"])
        messages.success(request, "Password changed. Your account is ready to use.")
        return redirect("dashboard")
    return render(request, "registration/password_change_required.html", {"form": form})

@login_required
def audit_log(request):
    _require_manage(request.user)
    team = _team(request.user)
    qs = AuditEvent.objects.filter(team=team).select_related("actor", "season")
    if not _is_admin(request.user):
        qs = qs.exclude(entity_type__in=FINANCE_AUDIT_ENTITY_TYPES)

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
    if selected_season.isdigit():
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
    entity_type_qs = AuditEvent.objects.filter(team=team).exclude(entity_type="")
    if not _is_admin(request.user):
        entity_type_qs = entity_type_qs.exclude(entity_type__in=FINANCE_AUDIT_ENTITY_TYPES)
    entity_types = entity_type_qs.values_list("entity_type", flat=True).distinct().order_by("entity_type")
    return render(request, "portal/finance_audit_log.html", {
        "events": page.object_list,
        "page_obj": page,
        "actions": AuditEvent.Action.choices,
        "seasons": Season.objects.filter(team=team).order_by("-start_date"),
        "entity_types": entity_types,
        "selected_action": selected_action,
        "selected_season": selected_season,
        "selected_entity": selected_entity,
        "entity_id": entity_id,
        "q": q,
        "filter_query": urlencode({k: v for k, v in params.items() if v}),
        "audit_title": "Team audit log",
        "audit_eyebrow": "OPERATIONS & CONTROLS",
        "audit_intro": "Immutable activity history for important team, competition, user, and finance changes.",
        "audit_back_url": "dashboard",
    })
