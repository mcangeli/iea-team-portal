"""Views for the roster domain."""

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


from .roster_helpers import (
    _team_roster,
    _visible_announcements,
)

@login_required
def dashboard(request):
    team = _team(request.user)
    if not team:
        return render(request, "portal/no_team.html")
    season = _active_season(team)
    now = timezone.now()
    today = timezone.localdate()
    announcements = _visible_announcements(request.user, team)[:5]
    events = team.events.filter(starts_at__gte=now)[:6]
    riders = _visible_riders(request.user, team).filter(active=True)
    shows = team.shows.filter(show_date__gte=today).order_by("show_date")[:4]
    memberships = season.memberships.select_related("rider") if season else SeasonMembership.objects.none()
    upcoming_lessons = Lesson.objects.none()
    volunteer_due = 0
    pending_volunteer = 0
    pending_availability = 0
    if season:
        upcoming_lessons = season.lessons.filter(starts_at__gte=now, cancelled=False).order_by("starts_at")
        if not _can_manage(request.user):
            upcoming_lessons = upcoming_lessons.filter(attendance__rider__in=riders).distinct()
        progress = _volunteer_progress_rows(season, riders)
        volunteer_due = sum(1 for row in progress if not row["complete"])
        pending_volunteer = VolunteerLog.objects.filter(season=season, rider__in=riders, status=VolunteerLog.Status.PENDING).count()
        upcoming_shows_qs = season.shows.filter(show_date__gte=today)
        for show in upcoming_shows_qs:
            for rider in riders:
                ShowAvailability.objects.get_or_create(show=show, rider=rider)
        pending_availability = ShowAvailability.objects.filter(show__in=upcoming_shows_qs, rider__in=riders, status=ShowAvailability.Status.PENDING).count()
    action_items = _visible_action_items(request.user, team).filter(completed=False)
    my_action_items = action_items.filter(
        Q(assigned_to=request.user) | Q(claimed_by=request.user) | Q(rider__in=riders)
    ).distinct().order_by("due_at", "-created_at")[:6]
    pending_event_rsvps = 0
    unclaimed_actions = 0
    overdue_actions = 0
    rsvp_events = list(team.events.filter(
        starts_at__gte=now, rsvp_requested=True, visible_to_all=True
    ))
    rider_list = list(riders)
    responded_pairs = set(
        EventRSVP.objects.filter(
            event__in=rsvp_events, rider__in=rider_list
        ).exclude(status=EventRSVP.Status.PENDING).values_list("event_id", "rider_id")
    )
    pending_event_rsvps = sum(
        1 for event in rsvp_events for rider in rider_list
        if (event.pk, rider.pk) not in responded_pairs
    )
    if _can_manage(request.user):
        unclaimed_actions = action_items.filter(
            claimable=True, claimed_by__isnull=True, assigned_to__isnull=True
        ).count()
        overdue_actions = action_items.filter(
            due_at__lt=now, completed=False
        ).count()

    next_show = shows.first() if shows else None
    qualifier_count = 0
    if season:
        qualifier_count = sum(
            1 for row in _qualification_rows(season)
            if row["qualified"] and row["rider"] in riders
        )
    attention_count = (
        pending_availability + pending_event_rsvps + len(my_action_items)
    )

    return render(request, "portal/dashboard.html", {
        "season": season, "announcements": announcements, "events": events, "riders": riders,
        "shows": shows, "can_manage": _can_manage(request.user),
        "futures_count": memberships.filter(team_level=SeasonMembership.TeamLevel.FUTURES).count(),
        "upper_count": memberships.filter(team_level=SeasonMembership.TeamLevel.UPPER).count(),
        "upcoming_lessons": upcoming_lessons[:4], "lesson_count": upcoming_lessons.count(),
        "volunteer_due": volunteer_due, "pending_volunteer": pending_volunteer,
        "pending_availability": pending_availability,
        "my_action_items": my_action_items,
        "pending_event_rsvps": pending_event_rsvps,
        "unclaimed_actions": unclaimed_actions,
        "overdue_actions": overdue_actions,
        "next_show": next_show,
        "roster_count": memberships.count() if season else riders.count(),
        "qualifier_count": qualifier_count,
        "attention_count": attention_count,
    })

@login_required
def my_team(request):
    team = _team(request.user)
    season = _active_season(team)
    riders = list(
        _visible_riders(request.user, team).filter(active=True).prefetch_related(
            "memberships__season", "guardian_links__guardian"
        ).order_by("last_name", "first_name")
    )
    now = timezone.now()
    upcoming_events = list(
        team.events.filter(starts_at__gte=now, visible_to_all=True)
        .prefetch_related("rsvps")
        .order_by("starts_at")[:12]
    )
    rider_ids = [r.pk for r in riders]
    rsvp_map = {
        (rsvp.event_id, rsvp.rider_id): rsvp
        for rsvp in EventRSVP.objects.filter(
            event__in=upcoming_events, rider_id__in=rider_ids
        ).select_related("rider")
    }
    event_rows = []
    for event in upcoming_events:
        responses = []
        if event.rsvp_requested:
            for rider in riders:
                responses.append({
                    "rider": rider,
                    "rsvp": rsvp_map.get((event.pk, rider.pk)),
                })
        event_rows.append({"event": event, "responses": responses})

    action_items = list(
        _visible_action_items(request.user, team)
        .filter(completed=False)
        .order_by("due_at", "-created_at")[:20]
    )
    memberships = {}
    if season:
        memberships = {
            m.rider_id: m
            for m in SeasonMembership.objects.filter(
                season=season, rider_id__in=rider_ids
            ).select_related("home_barn").prefetch_related("classes")
        }
    rider_rows = []
    for rider in riders:
        membership = memberships.get(rider.pk)
        rider_rows.append({
            "rider": rider,
            "membership": membership,
            "can_view_family_account": bool(membership and _can_view_family_account(request.user, membership)),
        })

    return render(request, "portal/my_team.html", {
        "team": team,
        "season": season,
        "rider_rows": rider_rows,
        "event_rows": event_rows,
        "action_items": action_items,
        "can_manage": _can_manage(request.user),
    })

@login_required
def rider_list(request):
    team = _team(request.user)
    qs = _team_roster(request.user, team).prefetch_related("memberships")
    season = _active_season(team)
    selected = _selected_team(request)
    if season:
        futures = qs.filter(memberships__season=season, memberships__team_level=SeasonMembership.TeamLevel.FUTURES).distinct()
        upper = qs.filter(memberships__season=season, memberships__team_level=SeasonMembership.TeamLevel.UPPER).distinct()
        unassigned = qs.exclude(memberships__season=season).distinct()
    else:
        futures = Rider.objects.none(); upper = Rider.objects.none(); unassigned = qs
    return render(request, "portal/rider_list.html", {
        "riders": qs, "futures": futures, "upper": upper, "unassigned": unassigned,
        "season": season, "can_manage": _can_manage(request.user), "selected_team": selected,
    })

@login_required
def rider_export(request):
    _require_manage(request.user)
    team = _team(request.user); season = _active_season(team); selected = _selected_team(request)
    qs = team.riders.filter(active=True).order_by("last_name", "first_name")
    if season and selected in TEAM_LEVELS:
        qs = qs.filter(memberships__season=season, memberships__team_level=selected).distinct()
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="rider-roster.csv"'
    writer = csv.writer(response)
    writer.writerow(["Rider", "Email", "Grade", "School", "Team", "Season classes", "IEA member number"])
    for rider in qs:
        membership = rider.memberships.filter(season=season).prefetch_related("classes").first() if season else None
        writer.writerow([
            str(rider), rider.email, rider.grade or "", rider.school,
            membership.get_team_level_display() if membership else "Unassigned",
            "; ".join(c.name for c in membership.classes.all()) if membership else "",
            rider.iea_member_number,
        ])
    return response

@login_required
def rider_detail(request, pk):
    team = _team(request.user)
    rider = get_object_or_404(Rider.objects.prefetch_related("memberships__classes", "guardian_links__guardian"), pk=pk, team=team)
    private_view = _can_view_private_rider(request.user, rider)
    active_season = _active_season(team)
    entries = rider.show_entries.filter(result__isnull=False)
    if active_season:
        entries = entries.filter(show_class__show__season=active_season)
    season_points = entries.aggregate(total=Sum("result__points"))["total"] or 0
    lesson_history = LessonAttendance.objects.none()
    volunteer_progress = None
    if active_season and private_view:
        lesson_history = rider.lesson_attendance.filter(lesson__season=active_season).select_related("lesson").order_by("-lesson__starts_at")[:10]
        progress_rows = _volunteer_progress_rows(active_season, Rider.objects.filter(pk=rider.pk))
        volunteer_progress = progress_rows[0] if progress_rows else None
    return render(request, "portal/rider_detail.html", {
        "rider": rider, "season_points": season_points, "can_manage": _can_manage(request.user),
        "active_season": active_season, "lesson_history": lesson_history, "volunteer_progress": volunteer_progress,
        "private_view": private_view,
    })

@login_required
@friendly_integrity_errors
def rider_create(request):
    _require_manage(request.user); team = _team(request.user)
    form = RiderForm(
        request.POST or None,
        request.FILES or None,
        team=team,
        include_season=True,
    )
    if form.is_valid():
        try:
            with transaction.atomic():
                obj = form.save(commit=False)
                obj.team = team
                obj.full_clean()
                obj.save()

                season = form.cleaned_data.get("season")
                if season:
                    membership = SeasonMembership.objects.create(
                        rider=obj,
                        season=season,
                        team_level=form.cleaned_data["team_level"],
                        home_barn=form.cleaned_data.get("home_barn"),
                        notes=form.cleaned_data.get("season_notes", ""),
                    )
                    membership.classes.set(form.cleaned_data.get("classes"))
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            if season:
                messages.success(
                    request,
                    f"Rider added and enrolled in {season.name}. The rider record will remain available for future seasons."
                )
            else:
                messages.success(
                    request,
                    "Rider added. No season enrollment was created; you can assign this rider to a season at any time."
                )
            return redirect("rider_detail", pk=obj.pk)
    return render(request, "portal/rider_form.html", {
        "form": form,
        "title": "Add rider",
        "eyebrow": "ROSTER",
        "creating": True,
    })

@login_required
def rider_edit(request, pk):
    _require_manage(request.user); team = _team(request.user)
    obj = get_object_or_404(Rider, pk=pk, team=team)
    form = RiderForm(request.POST or None, request.FILES or None, instance=obj, team=team)
    if form.is_valid():
        form.save(); messages.success(request, "Rider updated."); return redirect("rider_detail", pk=obj.pk)
    return render(request, "portal/rider_form.html", {
        "form": form,
        "title": "Edit rider",
        "eyebrow": "ROSTER",
        "creating": False,
    })

@login_required
def rider_membership_edit(request, pk, season_pk=None):
    _require_manage(request.user); team = _team(request.user)
    rider = get_object_or_404(Rider, pk=pk, team=team)
    season = get_object_or_404(Season, pk=season_pk, team=team) if season_pk else _active_season(team)
    if not season:
        messages.error(request, "Create or activate a season first."); return redirect("rider_detail", pk=rider.pk)
    _ensure_season_open(season)
    membership, _ = SeasonMembership.objects.get_or_create(rider=rider, season=season)
    form = SeasonMembershipForm(request.POST or None, instance=membership, season=season)
    if form.is_valid():
        form.save(); messages.success(request, f"{season.name} team and class assignments updated.")
        return redirect("rider_detail", pk=rider.pk)
    return render(request, "portal/form.html", {"form": form, "title": f"{rider.display_name} · {season.name}", "eyebrow": "SEASON ASSIGNMENT"})

@login_required
def rider_guardian_add(request, pk):
    _require_manage(request.user); team = _team(request.user)
    rider = get_object_or_404(Rider, pk=pk, team=team)
    form = GuardianContactForm(request.POST or None)
    if form.is_valid():
        relationship = form.cleaned_data.get("relationship", "")
        primary = form.cleaned_data.get("primary_contact", False)
        guardian = form.save(commit=False); guardian.team = team; guardian.save()
        RiderGuardian.objects.create(rider=rider, guardian=guardian, relationship=relationship, primary_contact=primary)
        messages.success(request, "Parent/guardian contact added."); return redirect("rider_detail", pk=rider.pk)
    return render(request, "portal/form.html", {"form": form, "title": f"Add parent/guardian · {rider.display_name}", "eyebrow": "FAMILY CONTACT"})

@login_required
def rider_guardian_edit(request, pk, guardian_pk):
    _require_manage(request.user); team = _team(request.user)
    rider = get_object_or_404(Rider, pk=pk, team=team)
    link = get_object_or_404(RiderGuardian.objects.select_related("guardian"), rider=rider, guardian_id=guardian_pk, guardian__team=team)
    form = GuardianContactForm(request.POST or None, instance=link.guardian, initial={"relationship": link.relationship, "primary_contact": link.primary_contact})
    if form.is_valid():
        form.save(); link.relationship = form.cleaned_data.get("relationship", ""); link.primary_contact = form.cleaned_data.get("primary_contact", False); link.save()
        messages.success(request, "Parent/guardian contact updated."); return redirect("rider_detail", pk=rider.pk)
    return render(request, "portal/form.html", {"form": form, "title": f"Edit {link.guardian.display_name}", "eyebrow": "FAMILY CONTACT"})

@login_required
def parent_list(request):
    _require_manage(request.user); team = _team(request.user); season = _active_season(team); selected = _selected_team(request)
    guardians = team.guardian_contacts.prefetch_related("rider_links__rider").all()
    if season and selected in TEAM_LEVELS:
        guardians = guardians.filter(rider_links__rider__memberships__season=season, rider_links__rider__memberships__team_level=selected).distinct()
    return render(request, "portal/parent_list.html", {"guardians": guardians, "selected_team": selected, "season": season})

@login_required
def parent_export(request):
    _require_manage(request.user); team = _team(request.user); season = _active_season(team); selected = _selected_team(request)
    guardians = team.guardian_contacts.prefetch_related("rider_links__rider").all()
    if season and selected in TEAM_LEVELS:
        guardians = guardians.filter(rider_links__rider__memberships__season=season, rider_links__rider__memberships__team_level=selected).distinct()
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="parent-guardian-directory.csv"'
    writer = csv.writer(response); writer.writerow(["Parent/Guardian", "Email", "Phone", "Riders", "Relationships"])
    for g in guardians:
        links = list(g.rider_links.select_related("rider").all())
        writer.writerow([g.display_name, g.email, g.phone, "; ".join(str(x.rider) for x in links), "; ".join(x.relationship for x in links if x.relationship)])
    return response

@login_required
def season_setup(request):
    _require_manage(request.user); team = _team(request.user); season = _active_season(team); selected = _selected_team(request)
    classes = season.season_classes.all() if season else SeasonClass.objects.none()
    memberships = season.memberships.select_related("rider").prefetch_related("classes") if season else SeasonMembership.objects.none()
    if selected in TEAM_LEVELS:
        memberships = memberships.filter(team_level=selected)
    return render(request, "portal/season_setup.html", {"season": season, "classes": classes, "memberships": memberships, "selected_team": selected})

@login_required
@friendly_integrity_errors
def season_class_create(request):
    _require_manage(request.user); team = _team(request.user); season = _active_season(team)
    if not season:
        messages.error(request, "Create or activate a season first."); return redirect("season_setup")
    initial = {"discipline": team.discipline if team.discipline != "multi" else "hunt_seat"}
    form = SeasonClassForm(request.POST or None, initial=initial, season=season)
    if form.is_valid():
        obj = form.save(commit=False); obj.season = season; obj.save()
        messages.success(request, "Season class added."); return redirect("season_setup")
    return render(request, "portal/form.html", {"form": form, "title": "Add season class", "eyebrow": season.name})

@login_required
def season_class_edit(request, class_pk):
    _require_manage(request.user); team = _team(request.user)
    season_class = get_object_or_404(SeasonClass.objects.select_related("season"), pk=class_pk, season__team=team)
    _ensure_season_open(season_class.season)
    form = SeasonClassForm(request.POST or None, instance=season_class, season=season_class.season)
    if form.is_valid():
        form.save(); messages.success(request, "Season class updated."); return redirect("season_setup")
    return render(request, "portal/form.html", {"form": form, "title": f"Edit {season_class.name}", "eyebrow": season_class.season.name})

@login_required
def rider_guardian_link(request, rider_pk):
    _require_manage(request.user)
    team = _team(request.user)
    rider = get_object_or_404(Rider, pk=rider_pk, team=team)

    existing_ids = RiderGuardian.objects.filter(rider=rider).values_list("guardian_id", flat=True)
    guardians = GuardianContact.objects.filter(team=team).exclude(pk__in=existing_ids).order_by("last_name", "first_name")

    if request.method == "POST":
        guardian_id = request.POST.get("guardian")
        if not guardian_id:
            messages.error(request, "Choose a parent/guardian to link.")
            return redirect("rider_guardian_link", rider_pk=rider.pk)
        relationship = (request.POST.get("relationship") or "Parent/Guardian").strip()
        primary_contact = request.POST.get("primary_contact") == "on"
        guardian = get_object_or_404(GuardianContact, pk=guardian_id, team=team)

        link, created = RiderGuardian.objects.get_or_create(
            rider=rider,
            guardian=guardian,
            defaults={
                "relationship": relationship,
                "primary_contact": primary_contact,
            },
        )
        if not created:
            messages.info(request, f"{guardian} is already linked to {rider}.")
        else:
            if guardian.user_id:
                rider.guardians.add(guardian.user)
            messages.success(request, f"{guardian} linked to {rider}.")
        return redirect("rider_detail", pk=rider.pk)

    return render(request, "portal/rider_guardian_link.html", {
        "rider": rider,
        "guardians": guardians,
    })

@login_required
@require_POST
def rider_guardian_unlink(request, rider_pk, link_pk):
    _require_manage(request.user)
    team = _team(request.user)
    rider = get_object_or_404(Rider, pk=rider_pk, team=team)
    link = get_object_or_404(RiderGuardian.objects.select_related("guardian"), pk=link_pk, rider=rider)

    guardian = link.guardian
    link.delete()

    if guardian.user_id:
        # Keep the legacy M2M only if this same user remains linked to the rider
        still_linked = RiderGuardian.objects.filter(rider=rider, guardian__user_id=guardian.user_id).exists()
        if not still_linked:
            rider.guardians.remove(guardian.user)

    messages.success(request, f"{guardian} unlinked from {rider}.")
    return redirect("rider_detail", pk=rider.pk)
