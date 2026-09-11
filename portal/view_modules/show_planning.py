"""Views for the show planning domain."""

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


from .show_planning_helpers import (
    _can_manage_planning_item,
)

@login_required
def show_planning(request, pk):
    team = _team(request.user)
    show = get_object_or_404(Show.objects.select_related("season"), pk=pk, team=team)
    can_plan = _can_plan_show(request.user, show)
    allowed_levels = _show_planning_allowed_levels(request.user, show)
    leads = show.lead_assignments.filter(active=True).select_related("user")
    all_items = list(show.planning_items.select_related("assigned_to", "claimed_by"))
    items = [item for item in all_items if _planning_item_visible_to_user(request.user, item)]
    for item in items:
        item.can_manage_item = _can_manage_planning_item(request.user, item)
        item.is_my_item = item.claimed_by_id == request.user.id or item.assigned_to_id == request.user.id
    return render(request, "portal/show_planning.html", {
        "show": show,
        "leads": leads,
        "items": items,
        "can_plan": can_plan,
        "allowed_levels": allowed_levels,
        "can_manage": _can_manage(request.user),
        "open_volunteer_count": sum(
            1 for item in items
            if item.item_type == ShowPlanningItem.ItemType.VOLUNTEER and not item.owner and not item.completed
        ),
        "incomplete_checklist_count": sum(
            1 for item in items
            if item.item_type == ShowPlanningItem.ItemType.CHECKLIST and not item.completed
        ),
    })

@login_required
@require_POST
def show_planning_seed_defaults(request, pk):
    team = _team(request.user)
    show = get_object_or_404(Show.objects.select_related("season"), pk=pk, team=team)
    if not (_can_manage(request.user) or _is_show_lead(request.user, show)):
        raise PermissionDenied
    _ensure_season_open(show.season)

    attending_defaults = [
        (ShowPlanningItem.ItemType.CHECKLIST, ShowPlanningItem.Category.TASK, "Confirm coach packet / paperwork", False),
        (ShowPlanningItem.ItemType.CHECKLIST, ShowPlanningItem.Category.TASK, "Confirm rider arrival plan", False),
        (ShowPlanningItem.ItemType.SUPPLY, ShowPlanningItem.Category.SUPPLY, "Team banner / signage", True),
        (ShowPlanningItem.ItemType.SUPPLY, ShowPlanningItem.Category.DRINK, "Team water / drinks", True),
        (ShowPlanningItem.ItemType.SUPPLY, ShowPlanningItem.Category.LUNCH, "Team lunch / food plan", True),
    ]
    hosting_defaults = attending_defaults + [
        (ShowPlanningItem.ItemType.CHECKLIST, ShowPlanningItem.Category.TASK, "Facility / ring setup complete", False),
        (ShowPlanningItem.ItemType.CHECKLIST, ShowPlanningItem.Category.TASK, "Officials / steward arrival confirmed", False),
        (ShowPlanningItem.ItemType.VOLUNTEER, ShowPlanningItem.Category.TASK, "Parking support", True),
        (ShowPlanningItem.ItemType.VOLUNTEER, ShowPlanningItem.Category.TASK, "Ring crew", True),
        (ShowPlanningItem.ItemType.VOLUNTEER, ShowPlanningItem.Category.TASK, "Hospitality support", True),
        (ShowPlanningItem.ItemType.VOLUNTEER, ShowPlanningItem.Category.TASK, "Awards support", True),
        (ShowPlanningItem.ItemType.VOLUNTEER, ShowPlanningItem.Category.TASK, "Cleanup crew", True),
        (ShowPlanningItem.ItemType.SUPPLY, ShowPlanningItem.Category.SUPPLY, "Awards / ribbons staged", False),
    ]

    defaults = (
        hosting_defaults
        if show.financial_role == Show.FinancialRole.HOSTING_ATTENDING
        else attending_defaults
    )
    existing_titles = set(show.planning_items.values_list("title", flat=True))
    created = 0
    for order, (item_type, category, title, family_visible) in enumerate(defaults, start=10):
        if title in existing_titles:
            continue
        ShowPlanningItem.objects.create(
            show=show,
            item_type=item_type,
            team_level=ShowPlanningItem.TeamLevel.ALL,
            category=category,
            title=title,
            family_visible=family_visible,
            sort_order=order * 10,
        )
        created += 1

    _audit_event(
        team=team, actor=request.user, action=AuditEvent.Action.GENERATED,
        obj=show, season=show.season,
        summary=f"Generated starter show-day plan for {show.name}",
        details={"items_created": created, "mode": show.financial_role},
    )
    if created:
        messages.success(request, f"Added {created} starter show-day item{'s' if created != 1 else ''}.")
    else:
        messages.info(request, "The starter show-day items are already present.")
    return redirect("show_planning", pk=show.pk)

@login_required
@friendly_integrity_errors
def show_lead_add(request, pk):
    _require_manage(request.user)
    team = _team(request.user); show = get_object_or_404(Show, pk=pk, team=team)
    form = ShowLeadAssignmentForm(request.POST or None, team=team, show=show)
    if form.is_valid():
        obj = form.save(commit=False); obj.show = show; obj.save()
        messages.success(request, "Show lead assigned."); return redirect("show_planning", pk=show.pk)
    return render(request, "portal/form.html", {"form": form, "title": f"Assign show lead · {show.name}", "eyebrow": "SHOW PLANNING"})

@login_required
def show_planning_item_add(request, pk):
    team = _team(request.user); show = get_object_or_404(Show, pk=pk, team=team)
    allowed_levels = _show_planning_allowed_levels(request.user, show)
    if not allowed_levels:
        raise PermissionDenied
    form = ShowPlanningItemForm(request.POST or None, team=team, allowed_team_levels=allowed_levels)
    if form.is_valid():
        obj = form.save(commit=False); obj.show = show
        if obj.team_level not in allowed_levels:
            raise PermissionDenied
        obj.save()
        _audit_event(
            team=team, actor=request.user, action=AuditEvent.Action.CREATED,
            obj=obj, season=show.season,
            summary=f"Added show-day {obj.get_item_type_display().lower()}: {obj.title}",
            details={"show": show, "team_level": obj.team_level},
        )
        messages.success(request, "Show planning item added."); return redirect("show_planning", pk=show.pk)
    return render(request, "portal/form.html", {"form": form, "title": f"Add show planning item · {show.name}", "eyebrow": "SHOW PLANNING"})

@login_required
def show_planning_item_edit(request, item_pk):
    team = _team(request.user); item = get_object_or_404(ShowPlanningItem.objects.select_related("show__season"), pk=item_pk, show__team=team)
    allowed_levels = _show_planning_allowed_levels(request.user, item.show)
    if not _can_manage_planning_item(request.user, item):
        raise PermissionDenied
    form = ShowPlanningItemForm(
        request.POST or None, instance=item, team=team, allowed_team_levels=allowed_levels
    )
    if form.is_valid():
        obj = form.save(commit=False)
        if obj.team_level not in allowed_levels:
            raise PermissionDenied
        obj.save()
        _audit_event(
            team=team, actor=request.user, action=AuditEvent.Action.UPDATED,
            obj=obj, season=item.show.season,
            summary=f"Updated show-day {obj.get_item_type_display().lower()}: {obj.title}",
            details={"show": item.show, "team_level": obj.team_level},
        )
        messages.success(request, "Show planning item updated."); return redirect("show_planning", pk=item.show_id)
    return render(request, "portal/form.html", {"form": form, "title": "Edit show planning item", "eyebrow": "SHOW PLANNING"})

@login_required
@require_POST
def show_planning_item_claim(request, item_pk):
    team = _team(request.user)
    item = get_object_or_404(
        ShowPlanningItem.objects.select_related("show__season"),
        pk=item_pk, show__team=team, family_visible=True
    )
    _ensure_season_open(item.show.season)
    if not _planning_item_visible_to_user(request.user, item):
        raise PermissionDenied
    can_manage_item = _can_manage_planning_item(request.user, item)
    if item.claimed_by_id and item.claimed_by_id != request.user.id and not can_manage_item:
        raise PermissionDenied
    if request.POST.get("clear") and (item.claimed_by_id == request.user.id or can_manage_item):
        item.claimed_by = None
    elif not item.claimed_by_id:
        item.claimed_by = request.user
    item.save(update_fields=["claimed_by"])
    return redirect("show_planning", pk=item.show_id)

@login_required
@require_POST
def show_planning_item_complete(request, item_pk):
    team = _team(request.user)
    item = get_object_or_404(
        ShowPlanningItem.objects.select_related("show__season"),
        pk=item_pk, show__team=team
    )
    _ensure_season_open(item.show.season)
    can_manage_item = _can_manage_planning_item(request.user, item)
    is_owner = item.claimed_by_id == request.user.id or item.assigned_to_id == request.user.id
    if not can_manage_item and not is_owner:
        raise PermissionDenied
    item.completed = not item.completed
    item.save(update_fields=["completed"])
    _audit_event(
        team=team, actor=request.user, action=AuditEvent.Action.UPDATED,
        obj=item, season=item.show.season,
        summary=f"{'Completed' if item.completed else 'Reopened'} show-day item: {item.title}",
        details={"show": item.show, "completed": item.completed},
    )
    if request.POST.get("return_to") == "my_show_day":
        return redirect("my_show_day", pk=item.show_id)
    return redirect("show_planning", pk=item.show_id)
