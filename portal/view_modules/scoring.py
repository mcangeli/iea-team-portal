"""Views for the scoring domain."""

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


@login_required
def standings(request):
    team = _team(request.user)
    season = _active_season(team)
    if not season:
        messages.error(request, "Create or activate a season before viewing standings.")
        return redirect("season_setup")
    selected = _selected_team(request)
    config, _ = SeasonScoringConfig.objects.get_or_create(season=season)
    individual = _qualification_rows(season, selected)
    can_manage = _can_manage(request.user)
    can_manage_points = _can_manage_points(request.user, season)
    team_rows, team_summary = _team_scoring_rows(season, selected, include_riders=can_manage_points)
    return render(request, "portal/standings.html", {
        "season": season, "config": config, "individual_rows": individual,
        "team_rows": team_rows, "team_summary": team_summary,
        "selected_team": selected, "can_manage": can_manage, "can_manage_points": can_manage_points,
    })

@login_required
def scoring_settings(request):
    _require_manage(request.user)
    team = _team(request.user); season = _active_season(team)
    if not season:
        messages.error(request, "Create or activate a season first."); return redirect("season_setup")
    config, _ = SeasonScoringConfig.objects.get_or_create(season=season)
    form = SeasonScoringConfigForm(request.POST or None, instance=config)
    if form.is_valid():
        form.save(); messages.success(request, "Season scoring and qualification rules updated."); return redirect("standings")
    return render(request, "portal/form.html", {"form": form, "title": "Scoring & qualification rules", "eyebrow": season.name})

@login_required
def qualification_override_edit(request, membership_pk, class_pk):
    team = _team(request.user)
    membership_probe = get_object_or_404(SeasonMembership.objects.select_related("season"), pk=membership_pk, season__team=team)
    if not _can_manage_points(request.user, membership_probe.season):
        raise PermissionDenied
    _ensure_season_open(membership_probe.season)
    membership = membership_probe
    membership = SeasonMembership.objects.select_related("rider", "season").get(pk=membership.pk)
    season_class = get_object_or_404(SeasonClass, pk=class_pk, season=membership.season)
    if not membership.classes.filter(pk=season_class.pk).exists():
        raise PermissionDenied("This rider is not assigned to that season class.")
    override, _ = QualificationOverride.objects.get_or_create(membership=membership, season_class=season_class)
    form = QualificationOverrideForm(request.POST or None, instance=override)
    if form.is_valid():
        obj = form.save()
        if obj.status == QualificationOverride.Status.AUTO and not obj.notes:
            obj.delete()
        messages.success(request, "Qualification status updated."); return redirect("standings")
    return render(request, "portal/form.html", {"form": form, "title": f"Qualification · {membership.rider}", "eyebrow": season_class.name})

@login_required
def standings_export(request):
    team = _team(request.user); season = _active_season(team)
    if season and not _can_manage_points(request.user, season):
        raise PermissionDenied
    if not season:
        return HttpResponse("No active season", status=400)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{season.name}-standings.csv"'
    writer = csv.writer(response)
    writer.writerow(["Individual qualification"])
    writer.writerow(["Team", "Rider", "Class", "Points", "Threshold", "Qualified"])
    for row in _qualification_rows(season):
        writer.writerow([row["membership"].get_team_level_display(), row["rider"], row["season_class"].name, row["points"], row["threshold"], "Yes" if row["qualified"] else "No"])
    writer.writerow([]); writer.writerow(["Team points"])
    writer.writerow(["Show", "Team", "Points rider", "Class", "Place", "Points"])
    team_rows, _ = _team_scoring_rows(season, include_riders=True)
    for row in team_rows:
        for cr in row["classes"]:
            result = cr["result"]
            writer.writerow([row["show"].name, row["team_label"], cr["entry"].rider, cr["entry"].show_class.display_name, result.place if result else "", cr["points"]])
    return response

@login_required
@require_POST
def point_rider_set(request, entry_pk):
    _require_manage(request.user); team = _team(request.user)
    entry = get_object_or_404(
        ShowEntry.objects.select_related("show_class__show", "rider"),
        pk=entry_pk, show_class__show__team=team,
    )
    show = entry.show_class.show
    _ensure_season_open(show.season)
    if show.competition_level != Show.CompetitionLevel.REGULAR:
        messages.error(
            request,
            "Finals use separate Individual and Team entries instead of regular-season point-rider designations."
        )
        return redirect("show_detail", pk=show.pk)
    if _is_non_team_scoring_class(entry.show_class):
        entry.is_point_rider = False
        entry.save(update_fields=["is_point_rider"])
        messages.error(
            request,
            f"{entry.show_class.display_name} is an H8/H14 Walk/Trot class and does not count toward team points."
        )
        return redirect("show_detail", pk=show.pk)
    membership = SeasonMembership.objects.filter(rider=entry.rider, season=show.season).first()
    if not membership:
        messages.error(request, "This rider is not on the season roster.")
        return redirect("show_detail", pk=show.pk)
    clear = request.POST.get("clear") == "1"
    if clear:
        entry.is_point_rider = False
        entry.save(update_fields=["is_point_rider"])
        messages.success(request, f"Cleared {entry.rider} as the points rider for {entry.show_class.display_name}.")
        return redirect("show_detail", pk=show.pk)
    for other in entry.show_class.entries.filter(is_point_rider=True).exclude(pk=entry.pk).select_related("rider"):
        other_membership = SeasonMembership.objects.filter(rider=other.rider, season=show.season).first()
        if other_membership and other_membership.team_level == membership.team_level:
            other.is_point_rider = False
            other.save(update_fields=["is_point_rider"])
    entry.is_point_rider = True
    update_fields = ["is_point_rider"]
    if entry.entry_type == ShowEntry.EntryType.INDIVIDUAL:
        entry.entry_type = ShowEntry.EntryType.BOTH
        update_fields.append("entry_type")
    entry.full_clean()
    entry.save(update_fields=update_fields)
    messages.success(request, f"{entry.rider} is the {membership.get_team_level_display()} points rider for {entry.show_class.display_name}.")
    return redirect("show_detail", pk=show.pk)
