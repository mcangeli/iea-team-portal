"""Views for the lessons domain."""

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


from .lessons_helpers import (
    _seed_lesson_attendance,
    _sync_lesson_calendar,
)

@login_required
def lesson_list(request):
    team = _team(request.user)
    season = _active_season(team)
    if not season:
        messages.error(request, "Create or activate a season before scheduling lessons.")
        return redirect("season_setup")
    lessons = season.lessons.select_related("group", "coach").prefetch_related("attendance__rider")
    if not _can_manage(request.user):
        visible = _visible_riders(request.user, team)
        lessons = lessons.filter(attendance__rider__in=visible).distinct()
    upcoming = lessons.filter(starts_at__gte=timezone.now()).order_by("starts_at")
    recent = lessons.filter(starts_at__lt=timezone.now()).order_by("-starts_at")[:12]
    return render(request, "portal/lesson_list.html", {
        "season": season, "upcoming": upcoming, "recent": recent, "can_manage": _can_manage(request.user),
    })

@login_required
def lesson_group_list(request):
    _require_manage(request.user)
    team = _team(request.user); season = _active_season(team)
    if not season:
        messages.error(request, "Create or activate a season first."); return redirect("season_setup")
    groups = season.lesson_groups.prefetch_related("riders").select_related("coach")
    return render(request, "portal/lesson_groups.html", {"season": season, "groups": groups})

@login_required
@friendly_integrity_errors
def lesson_group_create(request):
    _require_manage(request.user)
    team = _team(request.user); season = _active_season(team)
    if not season:
        messages.error(request, "Create or activate a season first."); return redirect("season_setup")
    form = LessonGroupForm(request.POST or None, season=season, team=team)
    if form.is_valid():
        obj = form.save(commit=False); obj.season = season; obj.save(); form.save_m2m()
        messages.success(request, "Lesson group created."); return redirect("lesson_group_list")
    return render(request, "portal/form.html", {"form": form, "title": "Create lesson group", "eyebrow": season.name})

@login_required
def lesson_group_edit(request, pk):
    _require_manage(request.user)
    team = _team(request.user); group = get_object_or_404(LessonGroup, pk=pk, season__team=team)
    _ensure_season_open(group.season)
    form = LessonGroupForm(request.POST or None, instance=group, season=group.season, team=team)
    if form.is_valid():
        form.save(); messages.success(request, "Lesson group updated."); return redirect("lesson_group_list")
    return render(request, "portal/form.html", {"form": form, "title": f"Edit {group.name}", "eyebrow": group.season.name})

@login_required
def lesson_create(request):
    _require_manage(request.user)
    team = _team(request.user); season = _active_season(team)
    if not season:
        messages.error(request, "Create or activate a season first."); return redirect("season_setup")
    form = LessonForm(request.POST or None, season=season, team=team)
    if form.is_valid():
        base = form.save(commit=False)
        weeks = form.cleaned_data.get("recurrence_weeks", 1)
        created = []
        for index in range(weeks):
            lesson = Lesson.objects.create(
                team=team, season=season, group=base.group, coach=base.coach,
                title=base.title,
                starts_at=base.starts_at + timedelta(weeks=index),
                ends_at=(base.ends_at + timedelta(weeks=index)) if base.ends_at else None,
                location=base.location or (base.group.default_location if base.group else ""),
                notes=base.notes, cancelled=base.cancelled,
            )
            _seed_lesson_attendance(lesson); _sync_lesson_calendar(lesson); created.append(lesson)
        messages.success(request, f"Created {len(created)} lesson{'s' if len(created) != 1 else ''}.")
        return redirect("lesson_list")
    return render(request, "portal/form.html", {"form": form, "title": "Schedule lesson", "eyebrow": season.name})

@login_required
def lesson_detail(request, pk):
    team = _team(request.user)
    lesson = get_object_or_404(Lesson.objects.select_related("season", "group", "coach"), pk=pk, team=team)
    visible = _visible_riders(request.user, team)
    attendance = lesson.attendance.select_related("rider")
    if not _can_manage(request.user):
        attendance = attendance.filter(rider__in=visible)
        if not attendance.exists():
            raise PermissionDenied
    return render(request, "portal/lesson_detail.html", {"lesson": lesson, "attendance": attendance, "can_manage": _can_manage(request.user)})

@login_required
def lesson_edit(request, pk):
    _require_manage(request.user)
    team = _team(request.user); lesson = get_object_or_404(Lesson, pk=pk, team=team)
    _ensure_season_open(lesson.season)
    form = LessonForm(request.POST or None, instance=lesson, season=lesson.season, team=team)
    if form.is_valid():
        obj = form.save(); _seed_lesson_attendance(obj); _sync_lesson_calendar(obj)
        messages.success(request, "Lesson updated."); return redirect("lesson_detail", pk=obj.pk)
    return render(request, "portal/form.html", {"form": form, "title": "Edit lesson", "eyebrow": lesson.season.name})

@login_required
def lesson_delete(request, pk):
    _require_manage(request.user)
    team = _team(request.user); lesson = get_object_or_404(Lesson, pk=pk, team=team)
    _ensure_season_open(lesson.season)
    if request.method == "POST":
        lesson.delete(); messages.success(request, "Lesson deleted."); return redirect("lesson_list")
    return render(request, "portal/confirm_delete.html", {"object": lesson, "title": "Delete lesson", "message": "Attendance and the linked calendar event will also be deleted."})

@login_required
def lesson_attendance_edit(request, attendance_pk):
    _require_manage(request.user)
    team = _team(request.user)
    attendance = get_object_or_404(LessonAttendance.objects.select_related("lesson__season", "rider"), pk=attendance_pk, lesson__team=team)
    _ensure_season_open(attendance.lesson.season)
    form = LessonAttendanceForm(request.POST or None, instance=attendance)
    if form.is_valid():
        form.save(); messages.success(request, f"Attendance updated for {attendance.rider}."); return redirect("lesson_detail", pk=attendance.lesson_id)
    return render(request, "portal/form.html", {"form": form, "title": f"Attendance · {attendance.rider}", "eyebrow": attendance.lesson.title})

@login_required
def show_availability(request, show_pk):
    team = _team(request.user); show = get_object_or_404(Show, pk=show_pk, team=team)
    roster = Rider.objects.filter(team=team, active=True, memberships__season=show.season).distinct().order_by("last_name", "first_name")
    if not _can_manage(request.user):
        roster = roster.filter(pk__in=_visible_riders(request.user, team).values("pk"))
    rows = []
    for rider in roster:
        response, _ = ShowAvailability.objects.get_or_create(show=show, rider=rider)
        rows.append(response)
    return render(request, "portal/show_availability.html", {"show": show, "responses": rows, "can_manage": _can_manage(request.user)})

@login_required
def show_availability_edit(request, show_pk, rider_pk):
    team = _team(request.user); show = get_object_or_404(Show, pk=show_pk, team=team)
    _ensure_season_open(show.season)
    rider = get_object_or_404(Rider, pk=rider_pk, team=team, memberships__season=show.season)
    if not _can_manage(request.user) and not _visible_riders(request.user, team).filter(pk=rider.pk).exists():
        raise PermissionDenied
    response, _ = ShowAvailability.objects.get_or_create(show=show, rider=rider)
    form = ShowAvailabilityForm(request.POST or None, instance=response)
    if form.is_valid():
        obj = form.save(commit=False); obj.responded_by = request.user
        obj.responded_at = timezone.now() if obj.status != ShowAvailability.Status.PENDING else None
        obj.save(); messages.success(request, f"Availability updated for {rider}."); return redirect("show_availability", show_pk=show.pk)
    return render(request, "portal/form.html", {"form": form, "title": f"Show availability · {rider}", "eyebrow": show.name})

@login_required
def volunteer_dashboard(request):
    team = _team(request.user); season = _active_season(team)
    if not season:
        messages.error(request, "Create or activate a season before tracking volunteer hours."); return redirect("season_setup")
    riders = team.riders.filter(active=True, memberships__season=season).distinct() if _can_manage(request.user) else _visible_riders(request.user, team).filter(active=True, memberships__season=season).distinct()
    rows = _volunteer_progress_rows(season, riders)
    logs = VolunteerLog.objects.filter(season=season, rider__in=riders).select_related("rider", "submitted_by", "approved_by")
    return render(request, "portal/volunteer_dashboard.html", {
        "season": season, "rows": rows, "logs": logs[:60], "can_manage": _can_manage(request.user),
        "pending_count": logs.filter(status=VolunteerLog.Status.PENDING).count(),
    })

@login_required
def volunteer_submit(request):
    team = _team(request.user); season = _active_season(team)
    if not season:
        messages.error(request, "Create or activate a season first."); return redirect("season_setup")
    visible = team.riders.filter(active=True) if _can_manage(request.user) else _visible_riders(request.user, team).filter(active=True)
    form = VolunteerLogForm(request.POST or None, team=team, season=season, visible_riders=visible)
    if form.is_valid():
        log = form.save(commit=False); log.season = season; log.submitted_by = request.user
        if _can_manage(request.user):
            log.status = VolunteerLog.Status.APPROVED; log.approved_by = request.user; log.approved_at = timezone.now()
        log.full_clean(); log.save()
        messages.success(request, "Volunteer hours recorded." if _can_manage(request.user) else "Volunteer hours submitted for coach approval.")
        return redirect("volunteer_dashboard")
    return render(request, "portal/form.html", {"form": form, "title": "Record volunteer hours", "eyebrow": season.name})

@login_required
def volunteer_review(request, pk):
    _require_manage(request.user)
    team = _team(request.user); log = get_object_or_404(VolunteerLog.objects.select_related("rider", "season"), pk=pk, season__team=team)
    _ensure_season_open(log.season)
    form = VolunteerReviewForm(request.POST or None, instance=log)
    if form.is_valid():
        obj = form.save(commit=False)
        if obj.status == VolunteerLog.Status.APPROVED:
            obj.approved_by = request.user; obj.approved_at = timezone.now()
        else:
            obj.approved_by = None; obj.approved_at = None
        obj.save(); messages.success(request, "Volunteer entry reviewed."); return redirect("volunteer_dashboard")
    return render(request, "portal/form.html", {"form": form, "title": f"Review volunteer hours · {log.rider}", "eyebrow": f"{log.hours} hours · {log.service_date:%b %d, %Y}"})

@login_required
def volunteer_requirements(request):
    _require_manage(request.user)
    team = _team(request.user); season = _active_season(team)
    if not season:
        messages.error(request, "Create or activate a season first."); return redirect("season_setup")
    form = VolunteerRequirementForm(request.POST or None, instance=season)
    if form.is_valid():
        form.save(); messages.success(request, "Volunteer-hour requirements updated."); return redirect("volunteer_dashboard")
    return render(request, "portal/form.html", {"form": form, "title": "Volunteer-hour requirements", "eyebrow": season.name})

@login_required
def volunteer_export(request):
    _require_manage(request.user)
    team = _team(request.user); season = _active_season(team)
    if not season:
        return HttpResponse("No active season", status=400)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{season.name}-volunteer-hours.csv"'
    writer = csv.writer(response)
    writer.writerow(["Team", "Rider", "Required", "Approved", "Pending", "Remaining", "Complete"])
    riders = team.riders.filter(active=True, memberships__season=season).distinct()
    for row in _volunteer_progress_rows(season, riders):
        writer.writerow([row["membership"].get_team_level_display(), row["rider"], row["required"], row["approved"], row["pending"], row["remaining"], "Yes" if row["complete"] else "No"])
    writer.writerow([])
    writer.writerow(["Rider", "Date", "Hours", "Category", "Performed by", "Description", "Status", "Submitted by", "Approved by"])
    for log in season.volunteer_logs.select_related("rider", "submitted_by", "approved_by"):
        writer.writerow([log.rider, log.service_date, log.hours, log.get_category_display(), log.performed_by, log.description, log.get_status_display(), log.submitted_by or "", log.approved_by or ""])
    return response
