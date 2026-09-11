"""Views for the competitions domain."""

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


from .competitions_helpers import (
    _sync_show_calendar,
)

@login_required
def show_list(request):
    team = _team(request.user); today = timezone.localdate(); selected = _selected_team(request)
    qs = team.shows.select_related("season")
    if selected in TEAM_LEVELS:
        qs = qs.filter(classes__season_class__team_level__in=[selected, SeasonClass.TeamLevel.BOTH]).distinct()
    upcoming = qs.filter(show_date__gte=today).order_by("show_date")
    past = qs.filter(show_date__lt=today).order_by("-show_date")[:20]
    return render(request, "portal/show_list.html", {"upcoming": upcoming, "past": past, "can_manage": _can_manage(request.user), "selected_team": selected})

@login_required
def show_detail(request, pk):
    team = _team(request.user)
    can_manage = _can_manage(request.user)
    show = get_object_or_404(Show.objects.select_related("season"), pk=pk, team=team)
    classes = show.classes.select_related("season_class").prefetch_related(
        "entries__rider", "entries__result", "entries__rider__memberships"
    )

    postseason_team_totals = []
    team_totals = {
        SeasonMembership.TeamLevel.FUTURES: 0,
        SeasonMembership.TeamLevel.UPPER: 0,
    }

    for show_class in classes:
        for entry in show_class.entries.all():
            membership = next(
                (m for m in entry.rider.memberships.all() if m.season_id == show.season_id),
                None,
            )
            if can_manage:
                entry.point_team_label = membership.get_team_level_display() if membership else "Team"

            entry.advances_to_zones = False
            if (
                show.competition_level == Show.CompetitionLevel.REGIONAL
                and entry.competition_track == ShowEntry.CompetitionTrack.INDIVIDUAL
            ):
                result = entry.result_or_none
                entry.advances_to_zones = bool(
                    result and result.place is not None and result.place <= 2
                )

            if (
                show.competition_level != Show.CompetitionLevel.REGULAR
                and entry.competition_track == ShowEntry.CompetitionTrack.TEAM
                and membership
                and membership.team_level in team_totals
                and not _is_non_team_scoring_class(show_class)
            ):
                result = entry.result_or_none
                if result and result.points is not None:
                    team_totals[membership.team_level] = (
                        team_totals.get(membership.team_level, 0) + result.points
                    )

    if show.competition_level != Show.CompetitionLevel.REGULAR:
        labels = dict(SeasonMembership.TeamLevel.choices)
        postseason_team_totals = [
            {
                "team_level": level,
                "team_label": labels[level],
                "points": points,
                "place": (
                    show.futures_team_place
                    if level == SeasonMembership.TeamLevel.FUTURES
                    else show.upper_team_place
                ),
                "advances_to_zones": (
                    show.competition_level == Show.CompetitionLevel.REGIONAL
                    and (
                        show.futures_team_place
                        if level == SeasonMembership.TeamLevel.FUTURES
                        else show.upper_team_place
                    ) == 1
                ),
            }
            for level, points in team_totals.items()
            if ShowEntry.objects.filter(
                show_class__show=show,
                competition_track=ShowEntry.CompetitionTrack.TEAM,
                rider__memberships__season=show.season,
                rider__memberships__team_level=level,
            ).exists()
        ]

    return render(request, "portal/show_detail.html", {
        "show": show,
        "classes": classes,
        "can_manage": can_manage,
        "can_finance_show": _can_finance(request.user, show.season),
        "postseason_team_totals": postseason_team_totals,
    })

@login_required
def show_create(request):
    _require_manage(request.user); team = _team(request.user); season = _active_season(team)
    if not season:
        messages.error(request, "Create or activate a season before adding a show."); return redirect("show_list")
    form = ShowForm(request.POST or None)
    if form.is_valid():
        obj = form.save(commit=False); obj.team = team; obj.season = season; obj.save(); _sync_show_calendar(obj)
        messages.success(request, "Show added and synced to the calendar."); return redirect("show_detail", pk=obj.pk)
    return render(request, "portal/form.html", {"form": form, "title": "Add show", "eyebrow": "COMPETITION"})

@login_required
def show_edit(request, pk):
    _require_manage(request.user); team = _team(request.user)
    show = get_object_or_404(Show.objects.select_related("season"), pk=pk, team=team)
    _ensure_season_open(show.season)
    form = ShowForm(request.POST or None, instance=show)
    if form.is_valid():
        form.save(); _sync_show_calendar(show); messages.success(request, "Show and calendar updated."); return redirect("show_detail", pk=show.pk)
    return render(request, "portal/form.html", {"form": form, "title": "Edit show", "eyebrow": "COMPETITION"})

@login_required
def show_delete(request, pk):
    _require_manage(request.user)
    team = _team(request.user)
    show = get_object_or_404(Show.objects.select_related("season"), pk=pk, team=team)
    _ensure_season_open(show.season)

    finance_links = {
        "ledger transaction": show.financial_transactions.count(),
        "family charge": show.family_charges.count(),
        "reimbursement request": show.reimbursement_requests.count(),
        "show allocation": show.financial_allocations.count(),
        "show budget item": show.show_budget_lines.count(),
    }
    blockers = [
        f"{count} {label}{'' if count == 1 else 's'}"
        for label, count in finance_links.items()
        if count
    ]
    if blockers:
        messages.error(
            request,
            "This show cannot be deleted because it is referenced by financial history: "
            + ", ".join(blockers)
            + ". Remove or reassign those finance records first."
        )
        return redirect("show_detail", pk=show.pk)

    if request.method == "POST":
        show.delete()
        messages.success(request, "Show deleted.")
        return redirect("show_list")
    return render(request, "portal/confirm_delete.html", {
        "object": show,
        "title": "Delete show",
        "message": "This also removes its show classes, entries, results, and linked calendar event.",
    })

@login_required
@friendly_integrity_errors
def show_class_create(request, show_pk):
    _require_manage(request.user); team = _team(request.user); show = get_object_or_404(Show, pk=show_pk, team=team)
    _ensure_season_open(show.season)
    if not show.season.season_classes.filter(active=True).exists():
        messages.error(request, "Set up season classes first, then add them to the show."); return redirect("season_setup")
    form = ShowClassForm(request.POST or None, show=show)
    if form.is_valid():
        obj = form.save(commit=False); obj.show = show; obj.save(); messages.success(request, "Season class added to this show."); return redirect("show_detail", pk=show.pk)
    return render(request, "portal/form.html", {"form": form, "title": "Add season class to show", "eyebrow": show.name})

@login_required
def show_class_edit(request, class_pk):
    _require_manage(request.user); team = _team(request.user)
    obj = get_object_or_404(ShowClass.objects.select_related("show__season"), pk=class_pk, show__team=team)
    _ensure_season_open(obj.show.season)
    form = ShowClassForm(request.POST or None, instance=obj, show=obj.show)
    if form.is_valid():
        form.save(); messages.success(request, "Show class updated."); return redirect("show_detail", pk=obj.show_id)
    return render(request, "portal/form.html", {"form": form, "title": f"Edit {obj.display_name}", "eyebrow": obj.show.name})

@login_required
def show_class_delete(request, class_pk):
    _require_manage(request.user); team = _team(request.user)
    obj = get_object_or_404(ShowClass.objects.select_related("show__season"), pk=class_pk, show__team=team); show_id = obj.show_id
    _ensure_season_open(obj.show.season)
    if request.method == "POST":
        obj.delete(); messages.success(request, "Show class and its entries removed."); return redirect("show_detail", pk=show_id)
    return render(request, "portal/confirm_delete.html", {"object": obj, "title": "Remove class from show", "message": "Entries and results recorded under this show class will also be deleted."})

@login_required
@friendly_integrity_errors
def show_entry_create(request, show_pk):
    _require_manage(request.user); team = _team(request.user); show = get_object_or_404(Show, pk=show_pk, team=team)
    _ensure_season_open(show.season)
    form = ShowEntryForm(request.POST or None, show=show, team=team)
    if form.is_valid():
        entry = form.save(commit=False)
        if entry.show_class.show_id != show.id or entry.rider.team_id != team.id: raise PermissionDenied
        entry.full_clean(); entry.save(); messages.success(request, "Rider entry added from season class assignment."); return redirect("show_detail", pk=show.pk)
    return render(request, "portal/form.html", {"form": form, "title": "Add rider entry", "eyebrow": show.name})

@login_required
def show_entry_edit(request, entry_pk):
    _require_manage(request.user); team = _team(request.user)
    entry = get_object_or_404(ShowEntry.objects.select_related("show_class__show__season", "rider"), pk=entry_pk, show_class__show__team=team); show = entry.show_class.show
    _ensure_season_open(show.season)
    form = ShowEntryForm(request.POST or None, instance=entry, show=show, team=team)
    if form.is_valid():
        obj = form.save(commit=False); obj.full_clean(); obj.save(); messages.success(request, "Rider entry updated."); return redirect("show_detail", pk=show.pk)
    return render(request, "portal/form.html", {"form": form, "title": f"Edit entry · {entry.rider}", "eyebrow": show.name})

@login_required
def show_entry_delete(request, entry_pk):
    _require_manage(request.user); team = _team(request.user)
    entry = get_object_or_404(ShowEntry.objects.select_related("show_class__show__season", "rider"), pk=entry_pk, show_class__show__team=team); show_id = entry.show_class.show_id
    _ensure_season_open(entry.show_class.show.season)
    if request.method == "POST":
        entry.delete(); messages.success(request, "Rider entry removed."); return redirect("show_detail", pk=show_id)
    return render(request, "portal/confirm_delete.html", {"object": entry, "title": "Remove rider entry", "message": "Any result attached to this entry will also be deleted."})

@login_required
def show_result_edit(request, entry_pk):
    team = _team(request.user)
    entry_probe = get_object_or_404(ShowEntry.objects.select_related("show_class__show__season"), pk=entry_pk, show_class__show__team=team)
    if not _can_manage_points(request.user, entry_probe.show_class.show.season):
        raise PermissionDenied
    _ensure_season_open(entry_probe.show_class.show.season)
    entry = get_object_or_404(ShowEntry.objects.select_related("show_class__show", "rider"), pk=entry_pk, show_class__show__team=team)
    result, created = ShowResult.objects.get_or_create(entry=entry); form = ShowResultForm(request.POST or None, instance=result)
    if form.is_valid():
        result = form.save()
        _audit_event(
            team=team, actor=request.user,
            action=AuditEvent.Action.CREATED if created else AuditEvent.Action.UPDATED,
            obj=result, season=entry.show_class.show.season,
            summary=f"Saved result for {entry.rider} · {entry.show_class.display_name}",
            details={"show": entry.show_class.show, "rider": entry.rider, "points": result.points},
        )
        messages.success(request, "Result saved.")
        return redirect("show_detail", pk=entry.show_class.show_id)
    return render(request, "portal/form.html", {"form": form, "title": f"Result · {entry.rider}", "eyebrow": entry.show_class.display_name})
