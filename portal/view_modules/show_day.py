"""Views for the show day domain."""

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


from .show_day_helpers import (
    _can_publish_show_update,
    _can_update_show_day_rider_status,
    _deliver_show_update,
    _parse_schedule_time,
    _rider_team_level_for_show,
    _shift_schedule_time,
    _show_day_operational_levels,
    _show_day_operational_user,
    _show_day_participating_riders,
    _show_update_allowed_audiences,
    _show_update_family_user_ids,
    _show_update_recipients,
    _visible_show_day_updates,
)

@login_required
def my_show_day(request, pk):
    team = _team(request.user)
    show = get_object_or_404(Show.objects.select_related("season"), pk=pk, team=team)

    personal_rider_ids = set(
        _personal_riders(request.user, team).values_list("id", flat=True)
    )
    participating = list(
        _show_day_participating_riders(show)
        .filter(pk__in=personal_rider_ids)
        .prefetch_related("memberships")
    )

    status_map = {
        obj.rider_id: obj
        for obj in ShowDayRiderStatus.objects.filter(
            show=show, rider_id__in=personal_rider_ids
        ).select_related("updated_by")
    }

    rider_rows = []
    for rider in participating:
        membership = next(
            (m for m in rider.memberships.all() if m.season_id == show.season_id),
            None,
        )
        status_obj = status_map.get(rider.pk)
        status_value = (
            status_obj.status if status_obj
            else ShowDayRiderStatus.Status.EXPECTED
        )
        rider_rows.append({
            "rider": rider,
            "membership": membership,
            "status_obj": status_obj,
            "status": status_value,
            "status_label": dict(ShowDayRiderStatus.Status.choices).get(
                status_value, status_value
            ),
            "can_edit": _can_update_show_day_rider_status(
                request.user, show, rider
            ),
        })

    classes = list(
        show.classes.select_related("season_class")
        .prefetch_related("entries__rider", "entries__result")
        .order_by("sort_order", "class_number", "name")
    )
    class_rows = []
    for show_class in classes:
        entries = [
            entry for entry in show_class.entries.all()
            if entry.status != ShowEntry.Status.SCRATCHED
            and entry.rider_id in personal_rider_ids
        ]
        if not entries:
            continue
        class_rows.append({
            "class": show_class,
            "entries": entries,
        })

    updates = list(_visible_show_day_updates(request.user, show)[:5])

    planning_items = list(
        show.planning_items.select_related("assigned_to", "claimed_by")
        .order_by("sort_order", "category", "title")
    )
    visible_planning = [
        item for item in planning_items
        if _planning_item_visible_to_user(request.user, item)
    ]
    my_assignments = [
        item for item in visible_planning
        if (
            item.claimed_by_id == request.user.id
            or item.assigned_to_id == request.user.id
        )
        and not item.completed
    ]
    open_family_jobs = [
        item for item in visible_planning
        if item.family_visible
        and item.item_type in {
            ShowPlanningItem.ItemType.VOLUNTEER,
            ShowPlanningItem.ItemType.SUPPLY,
        }
        and not item.owner
        and not item.completed
    ]

    return render(request, "portal/my_show_day.html", {
        "show": show,
        "rider_rows": rider_rows,
        "status_choices": ShowDayRiderStatus.Status.choices,
        "class_rows": class_rows,
        "recent_updates": updates,
        "my_assignments": my_assignments,
        "open_family_job_count": len(open_family_jobs),
        "has_personal_riders": bool(personal_rider_ids),
        "participating_count": len(participating),
    })

@login_required
def show_day_dashboard(request, pk):
    team = _team(request.user)
    show = get_object_or_404(Show.objects.select_related("season"), pk=pk, team=team)
    operational = _show_day_operational_user(request.user, show)

    participating = list(_show_day_participating_riders(show).prefetch_related("memberships"))
    status_map = {
        obj.rider_id: obj
        for obj in ShowDayRiderStatus.objects.filter(show=show).select_related("rider", "updated_by")
    }

    visible_rider_ids = set(_visible_riders(request.user, team).values_list("id", flat=True))
    operational_levels = _show_day_operational_levels(request.user, show) if operational else set()
    rows = []
    counts = {
        ShowDayRiderStatus.Status.EXPECTED: 0,
        ShowDayRiderStatus.Status.ARRIVED: 0,
        ShowDayRiderStatus.Status.RUNNING_LATE: 0,
        ShowDayRiderStatus.Status.SCRATCHED: 0,
        ShowDayRiderStatus.Status.FINISHED: 0,
    }

    operational_rider_ids = set()
    membership_by_rider = {}
    for rider in participating:
        membership = next((m for m in rider.memberships.all() if m.season_id == show.season_id), None)
        membership_by_rider[rider.pk] = membership

        in_operational_scope = bool(
            operational
            and (
                operational_levels is None
                or (membership and membership.team_level in operational_levels)
            )
        )
        if in_operational_scope:
            operational_rider_ids.add(rider.pk)

        if operational:
            if not in_operational_scope:
                continue
        elif rider.pk not in visible_rider_ids:
            continue

        status_obj = status_map.get(rider.pk)
        status_value = status_obj.status if status_obj else ShowDayRiderStatus.Status.EXPECTED
        if in_operational_scope:
            counts[status_value] = counts.get(status_value, 0) + 1

        can_edit = _can_update_show_day_rider_status(request.user, show, rider)
        rows.append({
            "rider": rider,
            "membership": membership,
            "status_obj": status_obj,
            "status": status_value,
            "status_label": dict(ShowDayRiderStatus.Status.choices).get(status_value, status_value),
            "can_edit": can_edit,
        })

    schedule_classes = list(
        show.classes.select_related("season_class")
        .prefetch_related("entries__rider", "entries__result")
        .order_by("sort_order", "class_number", "name")
    )

    schedule_rows = []
    results_missing = 0
    points_missing = 0

    for show_class in schedule_classes:
        active_entries = [
            e for e in show_class.entries.all()
            if e.status != ShowEntry.Status.SCRATCHED
        ]
        if not active_entries:
            continue

        if operational:
            relevant_entries = [
                e for e in active_entries if e.rider_id in operational_rider_ids
            ]
        else:
            relevant_entries = [e for e in active_entries if e.rider_id in visible_rider_ids]
        if not relevant_entries:
            continue

        result_count = sum(1 for e in relevant_entries if getattr(e, "result_or_none", None))
        missing_for_class = max(len(relevant_entries) - result_count, 0)
        results_missing += missing_for_class

        if show.competition_level == Show.CompetitionLevel.REGULAR:
            levels_present = {
                membership_by_rider[e.rider_id].team_level
                for e in relevant_entries
                if membership_by_rider.get(e.rider_id)
            }
            for level in levels_present:
                has_points_rider = any(
                    e.is_point_rider
                    and membership_by_rider.get(e.rider_id)
                    and membership_by_rider[e.rider_id].team_level == level
                    for e in relevant_entries
                )
                if not has_points_rider and not _is_non_team_scoring_class(show_class):
                    points_missing += 1

        schedule_rows.append({
            "class": show_class,
            "entries": relevant_entries,
            "missing_results": missing_for_class if operational else 0,
        })

    recent_updates = _visible_show_day_updates(request.user, show)[:4]

    planning_items_all = list(
        show.planning_items.select_related("assigned_to", "claimed_by").order_by("sort_order", "category", "title")
    )
    planning_items = [
        item for item in planning_items_all
        if _planning_item_visible_to_user(request.user, item)
    ]
    open_volunteers = [
        item for item in planning_items
        if item.item_type == ShowPlanningItem.ItemType.VOLUNTEER
        and not item.completed and not item.owner
    ]
    incomplete_checklist = [
        item for item in planning_items
        if item.item_type == ShowPlanningItem.ItemType.CHECKLIST and not item.completed
    ]
    my_assignments = [
        item for item in planning_items
        if (item.claimed_by_id or item.assigned_to_id) == request.user.id and not item.completed
    ]

    needs_attention = []
    if operational:
        if counts[ShowDayRiderStatus.Status.RUNNING_LATE]:
            needs_attention.append(f"{counts[ShowDayRiderStatus.Status.RUNNING_LATE]} rider(s) marked running late")
        expected_count = counts[ShowDayRiderStatus.Status.EXPECTED]
        if expected_count:
            needs_attention.append(f"{expected_count} rider(s) still expected / not checked in")
        if results_missing:
            needs_attention.append(f"{results_missing} result(s) not yet entered")
        if points_missing and _can_manage_points(request.user, show.season):
            needs_attention.append(f"{points_missing} class/team points-rider selection(s) may need attention")
        if any(not row["class"].schedule_time for row in schedule_rows):
            needs_attention.append("One or more classes do not have an estimated time")
        if open_volunteers:
            needs_attention.append(f"{len(open_volunteers)} volunteer position(s) are still unfilled")
        if incomplete_checklist:
            needs_attention.append(f"{len(incomplete_checklist)} checklist item(s) remain incomplete")

    return render(request, "portal/show_day_dashboard.html", {
        "show": show,
        "operational": operational,
        "rider_rows": rows,
        "status_choices": ShowDayRiderStatus.Status.choices,
        "counts": counts,
        "schedule_rows": schedule_rows[:8],
        "needs_attention": needs_attention,
        "recent_updates": recent_updates,
        "can_manage_points": _can_manage_points(request.user, show.season),
        "can_publish_update": _can_publish_show_update(request.user, show),
        "can_edit_schedule": bool(_show_schedule_edit_levels(request.user, show)),
        "open_volunteer_count": len(open_volunteers),
        "incomplete_checklist_count": len(incomplete_checklist),
        "my_assignments": my_assignments[:6],
        "planning_preview": planning_items[:6],
        "can_plan_show": _can_plan_show(request.user, show),
        "has_personal_riders": _personal_riders(request.user, team).exists(),
    })

@login_required
@require_POST
def show_day_rider_status_update(request, pk, rider_pk):
    team = _team(request.user)
    show = get_object_or_404(Show.objects.select_related("season"), pk=pk, team=team)
    _ensure_season_open(show.season)
    rider = get_object_or_404(_show_day_participating_riders(show), pk=rider_pk)

    if not _can_update_show_day_rider_status(request.user, show, rider):
        raise PermissionDenied

    status = request.POST.get("status", ShowDayRiderStatus.Status.EXPECTED)
    valid_statuses = {value for value, _ in ShowDayRiderStatus.Status.choices}
    if status not in valid_statuses:
        messages.error(request, "Choose a valid rider status.")
        if request.POST.get("return_to") == "my_show_day":
            return redirect("my_show_day", pk=show.pk)
        return redirect("show_day_dashboard", pk=show.pk)

    note = (request.POST.get("note") or "").strip()[:180]
    obj, created = ShowDayRiderStatus.objects.get_or_create(
        show=show,
        rider=rider,
        defaults={
            "status": status,
            "note": note,
            "updated_by": request.user,
        },
    )
    if not created:
        obj.status = status
        obj.note = note
        obj.updated_by = request.user
        obj.full_clean()
        obj.save(update_fields=["status", "note", "updated_by", "updated_at"])
    else:
        obj.full_clean()
        obj.save()

    _audit_event(
        team=team,
        actor=request.user,
        action=AuditEvent.Action.CREATED if created else AuditEvent.Action.UPDATED,
        obj=obj,
        season=show.season,
        summary=f"Show-day status: {rider.display_name} → {obj.get_status_display()}",
        details={"show": show, "rider": rider, "status": obj.status, "note": obj.note},
    )
    messages.success(request, f"{rider.display_name} marked {obj.get_status_display()}.")
    if request.POST.get("return_to") == "my_show_day":
        return redirect("my_show_day", pk=show.pk)
    return redirect("show_day_dashboard", pk=show.pk)

@login_required
def show_schedule(request, pk):
    team = _team(request.user)
    show = get_object_or_404(Show.objects.select_related("season"), pk=pk, team=team)
    classes = list(
        show.classes.select_related("season_class", "show")
        .prefetch_related("entries__rider", "entries__result")
        .order_by("sort_order", "class_number", "name")
    )
    editable_levels = _show_schedule_edit_levels(request.user, show)
    editable_ids = {c.pk for c in classes if c.team_level in editable_levels}

    if request.method == "POST":
        _ensure_season_open(show.season)
        action = request.POST.get("schedule_action", "save")

        if not editable_ids:
            raise PermissionDenied

        if action == "save":
            changed = 0
            errors = []
            for show_class in classes:
                if show_class.pk not in editable_ids:
                    continue
                try:
                    order_raw = (request.POST.get(f"order_{show_class.pk}") or "").strip()
                    if order_raw:
                        order = int(order_raw)
                        if order < 0:
                            raise ValueError
                    else:
                        order = show_class.sort_order

                    prize_time = _parse_schedule_time(request.POST.get(f"prize_{show_class.pk}"))
                    estimate_time = _parse_schedule_time(request.POST.get(f"estimate_{show_class.pk}"))
                    note = (request.POST.get(f"note_{show_class.pk}") or "").strip()[:180]
                except (ValueError, ValidationError) as exc:
                    errors.append(f"{show_class.display_name}: {exc}")
                    continue

                before = (
                    show_class.sort_order,
                    show_class.prize_list_time,
                    show_class.estimated_time,
                    show_class.schedule_note,
                )
                after = (order, prize_time, estimate_time, note)
                if before != after:
                    show_class.sort_order = order
                    show_class.prize_list_time = prize_time
                    show_class.estimated_time = estimate_time
                    show_class.schedule_note = note
                    show_class.save(update_fields=[
                        "sort_order", "prize_list_time", "estimated_time", "schedule_note",
                    ])
                    changed += 1

            if errors:
                for error in errors[:5]:
                    messages.error(request, error)
                if len(errors) > 5:
                    messages.error(request, f"{len(errors) - 5} additional schedule row(s) could not be saved.")
            if changed:
                _audit_event(
                    team=team, actor=request.user, action=AuditEvent.Action.UPDATED,
                    obj=show, season=show.season,
                    summary=f"Updated prize-list/show-day schedule for {show.name}",
                    details={"classes_changed": changed},
                )
                messages.success(request, f"Schedule updated for {changed} class{'es' if changed != 1 else ''}.")
            elif not errors:
                messages.info(request, "No schedule changes were detected.")

        elif action == "reset_estimates":
            changed = 0
            for show_class in classes:
                if show_class.pk not in editable_ids:
                    continue
                if show_class.estimated_time != show_class.prize_list_time:
                    show_class.estimated_time = show_class.prize_list_time
                    show_class.save(update_fields=["estimated_time"])
                    changed += 1
            _audit_event(
                team=team, actor=request.user, action=AuditEvent.Action.UPDATED,
                obj=show, season=show.season,
                summary=f"Reset show-day estimates to prize-list times for {show.name}",
                details={"classes_changed": changed},
            )
            messages.success(request, f"Reset {changed} class estimate{'s' if changed != 1 else ''} to prize-list times.")

        elif action == "shift":
            try:
                minutes = int(request.POST.get("shift_minutes", "0"))
            except ValueError:
                minutes = 0
            if minutes not in {-60, -30, -15, -10, 10, 15, 30, 60}:
                messages.error(request, "Choose one of the available schedule adjustments.")
                return redirect("show_schedule", pk=show.pk)

            start_id = request.POST.get("start_class")
            start_order = None
            if start_id and start_id.isdigit():
                start_class = next((c for c in classes if c.pk == int(start_id)), None)
                if start_class:
                    start_order = start_class.sort_order

            changed = 0
            for show_class in classes:
                if show_class.pk not in editable_ids:
                    continue
                if start_order is not None and show_class.sort_order < start_order:
                    continue
                current = show_class.schedule_time
                if current is None:
                    continue
                show_class.estimated_time = _shift_schedule_time(current, minutes)
                show_class.save(update_fields=["estimated_time"])
                changed += 1

            if changed:
                sign = "+" if minutes > 0 else ""
                _audit_event(
                    team=team, actor=request.user, action=AuditEvent.Action.UPDATED,
                    obj=show, season=show.season,
                    summary=f"Shifted show-day schedule {sign}{minutes} minutes for {show.name}",
                    details={
                        "minutes": minutes,
                        "classes_changed": changed,
                        "start_class_id": start_id or "",
                    },
                )
                messages.success(
                    request,
                    f"Shifted {changed} scheduled class{'es' if changed != 1 else ''} "
                    f"{abs(minutes)} minutes {'later' if minutes > 0 else 'earlier'}.",
                )
            else:
                messages.info(request, "No scheduled class times were available to shift.")
        else:
            messages.error(request, "Unknown schedule action.")

        return redirect("show_schedule", pk=show.pk)

    visible_rider_ids = set(_visible_riders(request.user, team).values_list("id", flat=True))
    my_class_ids = set(
        ShowEntry.objects.filter(
            show_class__show=show,
            rider_id__in=visible_rider_ids,
        )
        .exclude(status=ShowEntry.Status.SCRATCHED)
        .values_list("show_class_id", flat=True)
    )

    rows = []
    for show_class in classes:
        rows.append({
            "class": show_class,
            "editable": show_class.pk in editable_ids,
            "my_class": show_class.pk in my_class_ids,
            "entry_count": show_class.entries.exclude(status=ShowEntry.Status.SCRATCHED).count(),
        })

    return render(request, "portal/show_schedule.html", {
        "show": show,
        "rows": rows,
        "can_edit_any": bool(editable_ids),
        "editable_ids": editable_ids,
    })

@login_required
def show_day_updates(request, pk):
    team = _team(request.user)
    show = get_object_or_404(Show.objects.select_related("season"), pk=pk, team=team)
    updates = show.day_updates.filter(published=True).select_related("created_by", "updated_by")

    if not (_can_manage(request.user) or _is_show_lead(request.user, show)):
        visible_ids = []
        for update in updates:
            if _show_update_recipients(update).filter(pk=request.user.pk).exists():
                visible_ids.append(update.pk)
        updates = updates.filter(pk__in=visible_ids)

    return render(request, "portal/show_day_updates.html", {
        "show": show,
        "updates": updates,
        "can_publish": _can_publish_show_update(request.user, show),
        "allowed_audiences": _show_update_allowed_audiences(request.user, show),
    })

@login_required
def show_day_update_add(request, pk):
    team = _team(request.user)
    show = get_object_or_404(Show.objects.select_related("season"), pk=pk, team=team)
    allowed = _show_update_allowed_audiences(request.user, show)
    if not allowed:
        raise PermissionDenied
    _ensure_season_open(show.season)
    form = ShowDayUpdateForm(request.POST or None, allowed_audiences=allowed)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.show = show
        if obj.audience not in allowed:
            raise PermissionDenied
        obj.created_by = request.user
        obj.updated_by = request.user
        obj.full_clean()
        obj.save()
        delivered = 0
        if obj.published and form.cleaned_data.get("notify_now"):
            delivered = _deliver_show_update(obj)
        _audit_event(
            team=team, actor=request.user, action=AuditEvent.Action.CREATED,
            obj=obj, season=show.season,
            summary=f"Published show-day update: {obj.title}",
            details={"show": show.name, "audience": obj.audience, "notified": delivered},
        )
        messages.success(
            request,
            f"Show update saved" + (f" and sent to {delivered} portal user{'s' if delivered != 1 else ''}." if delivered else "."),
        )
        return redirect("show_day_updates", pk=show.pk)
    return render(request, "portal/form.html", {
        "form": form,
        "title": f"Post show update · {show.name}",
        "eyebrow": "SHOW DAY",
    })

@login_required
def show_day_update_edit(request, update_pk):
    team = _team(request.user)
    obj = get_object_or_404(
        ShowDayUpdate.objects.select_related("show__season"), pk=update_pk, show__team=team
    )
    show = obj.show
    allowed = _show_update_allowed_audiences(request.user, show)
    if obj.audience not in allowed:
        raise PermissionDenied
    _ensure_season_open(show.season)
    form = ShowDayUpdateForm(request.POST or None, instance=obj, allowed_audiences=allowed)
    if request.method != "POST":
        form.fields["notify_now"].initial = False
    if form.is_valid():
        obj = form.save(commit=False)
        if obj.audience not in allowed:
            raise PermissionDenied
        obj.updated_by = request.user
        obj.full_clean()
        obj.save()
        delivered = 0
        if obj.published and form.cleaned_data.get("notify_now"):
            delivered = _deliver_show_update(obj, revised=True)
        _audit_event(
            team=team, actor=request.user, action=AuditEvent.Action.UPDATED,
            obj=obj, season=show.season,
            summary=f"Updated public show-day information: {obj.title}",
            details={"show": show.name, "audience": obj.audience, "renotified": delivered},
        )
        messages.success(
            request,
            f"Show update revised" + (f" and a new notification was sent to {delivered} portal user{'s' if delivered != 1 else ''}." if delivered else "."),
        )
        return redirect("show_day_updates", pk=show.pk)
    return render(request, "portal/form.html", {
        "form": form,
        "title": f"Update public show information · {show.name}",
        "eyebrow": "SHOW DAY",
    })

@login_required
@require_POST
def show_day_update_retract(request, update_pk):
    team = _team(request.user)
    obj = get_object_or_404(
        ShowDayUpdate.objects.select_related("show__season"), pk=update_pk, show__team=team
    )
    if not _can_publish_show_update(request.user, obj.show, obj.audience):
        raise PermissionDenied
    _ensure_season_open(obj.show.season)
    obj.published = False
    obj.updated_by = request.user
    obj.save(update_fields=["published", "updated_by", "updated_at"])
    _audit_event(
        team=team, actor=request.user, action=AuditEvent.Action.REMOVED,
        obj=obj, season=obj.show.season,
        summary=f"Retracted public show-day update: {obj.title}",
        details={"show": obj.show.name, "audience": obj.audience},
    )
    messages.success(request, "Show update retracted. Existing notification history is retained.")
    return redirect("show_day_updates", pk=obj.show_id)

@login_required
def show_week_summary(request, pk):
    team = _team(request.user)
    show = get_object_or_404(Show.objects.select_related("season"), pk=pk, team=team)
    can_manage = _can_manage(request.user)
    classes = show.classes.select_related("season_class").prefetch_related("entries__rider", "entries__result")
    roster = Rider.objects.filter(show_entries__show_class__show=show).distinct().order_by("last_name", "first_name")
    availability = ShowAvailability.objects.filter(show=show, rider__in=roster).select_related("rider")
    if not can_manage:
        availability = availability.filter(rider__in=_visible_riders(request.user, team))
    return render(request, "portal/show_week_summary.html", {
        "show": show, "classes": classes, "roster": roster, "availability": availability, "can_manage": can_manage,
    })

@login_required
@require_POST
def show_week_summary_send(request, pk):
    _require_manage(request.user)
    team = _team(request.user)
    show = get_object_or_404(Show, pk=pk, team=team)
    riders = Rider.objects.filter(show_entries__show_class__show=show).distinct()
    recipient_ids = set(riders.exclude(user__isnull=True).values_list("user_id", flat=True))
    recipient_ids.update(GuardianContact.objects.filter(rider_links__rider__in=riders, user__isnull=False).values_list("user_id", flat=True))
    recipient_ids.update(User.objects.filter(profile__team=team, profile__role__in=[UserProfile.Role.ADMIN, UserProfile.Role.COACH]).values_list("id", flat=True))
    title = f"Show week: {show.name}"
    body = f"{show.name} is {show.show_date:%A, %B %d}. Check the portal for entries, schedule, venue, and your availability status."
    created = 0
    for user in User.objects.filter(id__in=recipient_ids, is_active=True).select_related("profile"):
        notification = Notification.objects.create(user=user, title=title, body=body, link=f"/shows/{show.pk}/week/")
        created += 1
        profile = getattr(user, "profile", None)
        if settings.EMAIL_HOST and user.email and (not profile or profile.email_reminders):
            send_mail(title, body, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
    messages.success(request, f"Show-week summary sent to {created} portal user{'s' if created != 1 else ''}.")
    return redirect("show_week_summary", pk=show.pk)
