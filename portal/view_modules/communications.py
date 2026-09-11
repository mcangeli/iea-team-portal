"""Views for the communications domain."""

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


from .communications_helpers import (
    _deliver_announcement,
)

@login_required
def event_rsvp(request, pk, rider_pk):
    team = _team(request.user)
    event = get_object_or_404(CalendarEvent, pk=pk, team=team, rsvp_requested=True)
    rider = get_object_or_404(_visible_riders(request.user, team), pk=rider_pk)
    rsvp, _ = EventRSVP.objects.get_or_create(event=event, rider=rider)
    form = EventRSVPForm(request.POST or None, instance=rsvp)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.responded_by = request.user
        obj.save()
        messages.success(request, f"RSVP updated for {rider.display_name}.")
        return redirect("my_team")
    return render(request, "portal/form.html", {
        "form": form,
        "title": f"RSVP · {event.title}",
        "eyebrow": rider.display_name,
    })

@login_required
def action_item_list(request):
    team = _team(request.user)
    items = _visible_action_items(request.user, team)
    show_completed = request.GET.get("completed") == "1"
    if not show_completed:
        items = items.filter(completed=False)
    return render(request, "portal/action_item_list.html", {
        "items": items[:100],
        "can_manage": _can_manage(request.user),
        "show_completed": show_completed,
    })

@login_required
def action_item_create(request):
    _require_manage(request.user)
    team = _team(request.user)
    season = _active_season(team)
    form = ActionItemForm(request.POST or None, team=team, season=season)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.team = team
        obj.season = season
        obj.created_by = request.user
        obj.save()
        messages.success(request, "Action item created.")
        return redirect("action_item_list")
    return render(request, "portal/form.html", {
        "form": form, "title": "Add action item", "eyebrow": "TEAM HUB"
    })

@login_required
def action_item_edit(request, pk):
    _require_manage(request.user)
    team = _team(request.user)
    item = get_object_or_404(ActionItem, pk=pk, team=team)
    form = ActionItemForm(request.POST or None, instance=item, team=team, season=item.season)
    if form.is_valid():
        form.save()
        messages.success(request, "Action item updated.")
        return redirect("action_item_list")
    return render(request, "portal/form.html", {
        "form": form, "title": f"Edit · {item.title}", "eyebrow": "TEAM HUB"
    })

@login_required
@require_POST
def action_item_claim(request, pk):
    team = _team(request.user)
    item = get_object_or_404(_visible_action_items(request.user, team), pk=pk, completed=False)
    if not item.claimable:
        raise PermissionDenied
    if item.claimed_by_id and item.claimed_by_id != request.user.id and not _can_manage(request.user):
        messages.error(request, "This item has already been claimed.")
    else:
        item.claimed_by = None if item.claimed_by_id == request.user.id else request.user
        item.save(update_fields=["claimed_by"])
        messages.success(request, "Action item updated.")
    return redirect("action_item_list")

@login_required
@require_POST
def action_item_complete(request, pk):
    team = _team(request.user)
    item = get_object_or_404(_visible_action_items(request.user, team), pk=pk)
    allowed = _can_manage(request.user) or item.assigned_to_id == request.user.id or item.claimed_by_id == request.user.id
    if not allowed:
        raise PermissionDenied
    item.completed = not item.completed
    item.save()
    messages.success(request, "Action item updated.")
    return redirect("action_item_list")

@login_required
def calendar(request):
    team = _team(request.user)
    selected_kind = request.GET.get("kind", "all")
    valid_kinds = {value for value, _label in CalendarEvent.Kind.choices}
    events = team.events.select_related("show", "lesson").all()
    if not _can_manage(request.user):
        events = events.filter(visible_to_all=True)
    if selected_kind in valid_kinds:
        events = events.filter(kind=selected_kind)
    else:
        selected_kind = "all"
    return render(request, "portal/calendar.html", {
        "events": events[:100], "can_manage": _can_manage(request.user),
        "selected_kind": selected_kind, "event_kinds": CalendarEvent.Kind.choices,
    })

@login_required
def event_create(request):
    _require_manage(request.user); team = _team(request.user)
    form = CalendarEventForm(request.POST or None)
    if form.is_valid():
        obj = form.save(commit=False); obj.team = team; obj.season = _active_season(team); obj.save()
        messages.success(request, "Calendar event added."); return redirect("calendar")
    return render(request, "portal/form.html", {"form": form, "title": "Add calendar event", "eyebrow": "SCHEDULE"})

@login_required
def event_edit(request, pk):
    _require_manage(request.user)
    team = _team(request.user)
    event = get_object_or_404(CalendarEvent.objects.select_related("show", "lesson"), pk=pk, team=team)

    if event.show_id:
        messages.info(request, "This calendar entry is synced from a show. Edit the show to update the calendar.")
        return redirect("show_edit", pk=event.show_id)
    if event.lesson_id:
        messages.info(request, "This calendar entry is synced from a lesson. Edit the lesson to update the calendar.")
        return redirect("lesson_edit", pk=event.lesson_id)

    form = CalendarEventForm(request.POST or None, instance=event)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.team = team
        obj.save()
        messages.success(request, "Calendar event updated.")
        return redirect("calendar")
    return render(request, "portal/form.html", {
        "form": form,
        "title": f"Edit calendar event · {event.title}",
        "eyebrow": "SCHEDULE",
    })

@login_required
def event_delete(request, pk):
    _require_manage(request.user)
    team = _team(request.user)
    event = get_object_or_404(CalendarEvent.objects.select_related("show", "lesson"), pk=pk, team=team)

    if event.show_id:
        messages.info(request, "This calendar entry is synced from a show. Manage the show instead of deleting the calendar copy.")
        return redirect("show_edit", pk=event.show_id)
    if event.lesson_id:
        messages.info(request, "This calendar entry is synced from a lesson. Manage the lesson instead of deleting the calendar copy.")
        return redirect("lesson_edit", pk=event.lesson_id)

    if request.method == "POST":
        title = event.title
        event.delete()
        messages.success(request, f"Calendar event ‘{title}’ deleted.")
        return redirect("calendar")

    return render(request, "portal/confirm_delete.html", {
        "object": event,
        "title": f"Delete calendar event · {event.title}",
        "message": "This will permanently remove this manually-created calendar event. It will not delete any rider, show, lesson, or other team record.",
    })

@login_required
def announcement_create(request):
    _require_manage(request.user); team = _team(request.user)
    form = AnnouncementForm(request.POST or None, team=team)
    if form.is_valid():
        obj = form.save(commit=False); obj.team = team; obj.season = _active_season(team); obj.created_by = request.user; obj.save(); form.save_m2m()
        recipient_count = _deliver_announcement(obj) if obj.published else 0
        messages.success(request, f"Announcement posted to {recipient_count} portal user{'s' if recipient_count != 1 else ''}."); return redirect("dashboard")
    return render(request, "portal/form.html", {"form": form, "title": "Post announcement", "eyebrow": "TEAM NEWS"})

@login_required
def notification_list(request):
    notifications = request.user.portal_notifications.select_related("announcement", "show_day_update").all()[:100]
    return render(request, "portal/notifications.html", {"notifications": notifications})

@login_required
@require_POST
def notification_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    if not notification.read_at:
        notification.read_at = timezone.now(); notification.save(update_fields=["read_at"])
    return redirect(notification.link or "notification_list")

@login_required
@require_POST
def notification_read_all(request):
    request.user.portal_notifications.filter(read_at__isnull=True).update(read_at=timezone.now())
    return redirect("notification_list")

@login_required
def notification_preferences(request):
    if not hasattr(request.user, "profile"):
        raise PermissionDenied
    form = NotificationPreferenceForm(request.POST or None, instance=request.user.profile)
    if form.is_valid():
        form.save(); messages.success(request, "Notification preferences updated."); return redirect("notification_list")
    return render(request, "portal/form.html", {"form": form, "title": "Notification preferences", "eyebrow": "COMMUNICATIONS"})
