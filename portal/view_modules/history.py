"""Views for the history domain."""

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


from .history_helpers import (
    _accessiea_show_column,
    _accessiea_split_name,
    _accessiea_team_level,
    _historical_import_bootstrap_counts,
    _historical_import_commit,
    _historical_import_preview,
    _historical_import_preview_accessiea,
    _historical_import_preview_standard,
    _history_import_date,
    _history_import_decimal,
    _history_import_int,
    _history_import_level,
    _history_import_norm,
    _history_import_track,
    _season_archive_readiness,
    _season_rider_summary,
)

@login_required
def season_archive(request):
    team = _team(request.user)
    seasons = list(
        Season.objects.filter(team=team)
        .annotate(
            history_rider_count=Count("memberships", distinct=True),
            history_show_count=Count("shows", distinct=True),
            history_result_count=Count("shows__classes__entries__result", distinct=True),
        )
        .order_by("-start_date")
    )
    return render(request, "portal/season_archive.html", {
        "seasons": seasons,
        "can_manage": _can_manage(request.user),
        "is_admin": _is_admin(request.user),
    })

@login_required
def season_history_entry(request, season_pk):
    """Manager workspace for entering and reviewing records from a prior season."""
    _require_manage(request.user)
    team = _team(request.user)
    season = get_object_or_404(Season, pk=season_pk, team=team)
    reconciliation_key = f"historical_import_last_{season.pk}_{request.user.pk}"
    import_reconciliation = request.session.pop(reconciliation_key, None)

    memberships = list(
        season.memberships.select_related("rider")
        .prefetch_related("classes")
        .annotate(
            history_result_count=Count(
                "rider__show_entries__result",
                filter=Q(rider__show_entries__show_class__show__season=season),
                distinct=True,
            ),
            history_show_count=Count(
                "rider__show_entries__show_class__show",
                filter=Q(rider__show_entries__show_class__show__season=season),
                distinct=True,
            ),
        )
        .order_by("rider__last_name", "rider__first_name")
    )
    rider_rows = [
        {
            "membership": membership,
            "rider": membership.rider,
            "result_count": membership.history_result_count,
            "show_count": membership.history_show_count,
        }
        for membership in memberships
    ]

    season_totals = season.shows.aggregate(
        show_count=Count("id", distinct=True),
        result_count=Count("classes__entries__result", distinct=True),
    )

    return render(request, "portal/season_history_entry.html", {
        "season": season,
        "rider_rows": rider_rows,
        "show_count": season_totals["show_count"],
        "result_count": season_totals["result_count"],
        "is_admin": _is_admin(request.user),
        "import_reconciliation": import_reconciliation,
    })

@login_required
def season_history_import(request, season_pk):
    _require_manage(request.user)
    team = _team(request.user)
    season = get_object_or_404(Season, pk=season_pk, team=team)
    session_key = f"historical_import_preview_{season.pk}_{request.user.pk}"

    upload_form = HistoricalImportUploadForm(
        request.POST or None,
        request.FILES or None,
    )
    preview_rows = request.session.get(session_key, [])
    preview_ready = bool(preview_rows)
    error_count = sum(1 for row in preview_rows if row.get("errors"))
    duplicate_count = sum(1 for row in preview_rows if row.get("duplicate"))
    ready_count = sum(1 for row in preview_rows if row.get("ready"))
    bootstrap_counts = _historical_import_bootstrap_counts(preview_rows)

    if request.method == "POST":
        action = request.POST.get("action", "preview")

        if action == "clear":
            request.session.pop(session_key, None)
            messages.info(request, "Import preview cleared.")
            return redirect("season_history_import", season_pk=season.pk)

        if action == "commit":
            if not preview_rows:
                messages.error(request, "Upload and preview a CSV before importing.")
                return redirect("season_history_import", season_pk=season.pk)
            if error_count:
                messages.error(
                    request,
                    "Fix the validation errors in the CSV and preview it again before importing."
                )
                return redirect("season_history_import", season_pk=season.pk)
            try:
                import_stats = _historical_import_commit(season, preview_rows)
            except ValidationError as exc:
                for message in exc.messages:
                    messages.error(request, message)
                return redirect("season_history_import", season_pk=season.pk)

            _audit_event(
                team=team,
                actor=request.user,
                action=AuditEvent.Action.CREATED,
                obj=season,
                season=season,
                summary=f"Historical CSV import: {season.name}",
                details={
                    **import_stats,
                    "rows_previewed": len(preview_rows),
                },
            )
            request.session.pop(session_key, None)
            request.session[
                f"historical_import_last_{season.pk}_{request.user.pk}"
            ] = {
                **import_stats,
                "rows_previewed": len(preview_rows),
                "warnings": sum(len(row.get("warnings", [])) for row in preview_rows),
                "errors": 0,
            }
            request.session.modified = True
            setup_parts = []
            if import_stats["riders_created"]:
                setup_parts.append(f"{import_stats['riders_created']} rider(s)")
            if import_stats["memberships_created"]:
                setup_parts.append(f"{import_stats['memberships_created']} season membership(s)")
            if import_stats["classes_created"]:
                setup_parts.append(f"{import_stats['classes_created']} season class(es)")
            if import_stats["class_assignments_created"]:
                setup_parts.append(f"{import_stats['class_assignments_created']} class assignment(s)")
            if import_stats["iea_numbers_added"]:
                setup_parts.append(f"{import_stats['iea_numbers_added']} IEA number(s)")
            setup_text = (
                " Historical setup created: " + ", ".join(setup_parts) + "."
                if setup_parts else ""
            )
            created = import_stats["results_created"]
            skipped = import_stats["duplicates_skipped"]
            messages.success(
                request,
                f"Historical import complete: {created} result"
                f"{'s' if created != 1 else ''} created, "
                f"{skipped} duplicate{'s' if skipped != 1 else ''} skipped."
                f"{setup_text}"
            )
            return redirect("season_history_entry", season_pk=season.pk)

        if action == "preview" and upload_form.is_valid():
            try:
                preview_rows = _historical_import_preview(
                    season,
                    upload_form.cleaned_data["csv_file"],
                    bootstrap_missing=upload_form.cleaned_data.get("bootstrap_missing", False),
                )
            except ValidationError as exc:
                for message in exc.messages:
                    messages.error(request, message)
                preview_rows = []
                request.session.pop(session_key, None)
            else:
                request.session[session_key] = preview_rows
                request.session.modified = True
                error_count = sum(
                    1 for row in preview_rows if row.get("errors")
                )
                duplicate_count = sum(
                    1 for row in preview_rows if row.get("duplicate")
                )
                ready_count = sum(
                    1 for row in preview_rows if row.get("ready")
                )
                bootstrap_counts = _historical_import_bootstrap_counts(preview_rows)
                preview_ready = True
                if error_count:
                    messages.warning(
                        request,
                        f"Preview found {error_count} row"
                        f"{'s' if error_count != 1 else ''} with errors."
                    )
                else:
                    messages.success(
                        request,
                        f"Preview ready: {ready_count} new result"
                        f"{'s' if ready_count != 1 else ''} and "
                        f"{duplicate_count} duplicate"
                        f"{'s' if duplicate_count != 1 else ''}."
                    )

    return render(request, "portal/season_history_import.html", {
        "season": season,
        "upload_form": upload_form,
        "preview_rows": preview_rows,
        "preview_ready": preview_ready,
        "error_count": error_count,
        "duplicate_count": duplicate_count,
        "ready_count": ready_count,
        "bootstrap_counts": bootstrap_counts,
    })

@login_required
def season_history_import_template(request, season_pk):
    _require_manage(request.user)
    team = _team(request.user)
    season = get_object_or_404(Season, pk=season_pk, team=team)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="historical-results-{season.pk}-template.csv"'
    )
    writer = csv.writer(response)
    writer.writerow(HISTORICAL_IMPORT_HEADERS)

    membership = (
        season.memberships.select_related("rider")
        .prefetch_related("classes")
        .order_by("rider__last_name", "rider__first_name")
        .first()
    )
    rider = membership.rider if membership else None
    season_class = membership.classes.order_by("sort_order", "name").first() if membership else None
    writer.writerow([
        rider.first_name if rider else "Emma",
        rider.last_name if rider else "Brown",
        "Example Fall Show",
        season.start_date.isoformat(),
        "regular",
        season_class.name if season_class else "Intermediate Flat",
        "",
        "2",
        "",
        "Example Horse",
        "Example Venue",
        "Optional source note",
        "",
        "",
    ])
    return response

@login_required
def season_archive_readiness(request, season_pk):
    if not _is_admin(request.user):
        raise PermissionDenied
    team = _team(request.user)
    season = get_object_or_404(Season, pk=season_pk, team=team)
    readiness = _season_archive_readiness(season)
    return render(request, "portal/season_archive_readiness.html", {
        "season": season,
        "readiness": readiness,
        "is_admin": True,
    })

@login_required
def season_review(request, season_pk):
    team = _team(request.user)
    season = get_object_or_404(Season, pk=season_pk, team=team)
    points_access = _can_manage_points(request.user, season)
    if _can_manage(request.user) or points_access:
        riders = Rider.objects.filter(memberships__season=season).distinct().order_by("last_name", "first_name")
    else:
        riders = _visible_riders(request.user, team).filter(memberships__season=season).distinct()
    rider_rows = _season_rider_summary(season, riders)
    for row in rider_rows:
        row["can_history"] = _can_view_private_rider(request.user, row["rider"])
    qualification_rows = _qualification_rows(season) if points_access else [
        row for row in _qualification_rows(season) if row["rider"].pk in {r.pk for r in riders}
    ]
    awards = RiderAward.objects.filter(season=season, published=True).select_related("rider")
    if not (_can_manage(request.user) or points_access):
        awards = awards.filter(rider__in=riders)
    team_rows, team_summary = _team_scoring_rows(season, include_riders=points_access)
    postseason_results = ShowResult.objects.filter(
        entry__show_class__show__season=season,
        entry__show_class__show__competition_level__in=[
            Show.CompetitionLevel.REGIONAL,
            Show.CompetitionLevel.ZONE,
            Show.CompetitionLevel.NATIONAL,
        ],
    ).select_related(
        "entry__rider", "entry__show_class__show", "entry__show_class__season_class"
    ).order_by(
        "entry__show_class__show__show_date",
        "entry__show_class__sort_order",
        "entry__rider__last_name",
    )
    if not (_can_manage(request.user) or points_access):
        postseason_results = postseason_results.filter(entry__rider__in=riders)
    return render(request, "portal/season_review.html", {
        "season": season, "rider_rows": rider_rows, "qualification_rows": qualification_rows,
        "awards": awards, "team_summary": team_summary, "can_manage": _can_manage(request.user),
        "can_manage_points": points_access, "postseason_results": postseason_results,
        "is_admin": _is_admin(request.user),
    })

@login_required
@require_POST
def season_close(request, season_pk):
    if not _is_admin(request.user):
        raise PermissionDenied
    team = _team(request.user)
    season = get_object_or_404(Season, pk=season_pk, team=team)
    if season.is_closed:
        messages.info(request, f"{season.name} is already archived.")
        return redirect("season_review", season_pk=season.pk)

    if request.POST.get("confirm_archive") != "yes":
        messages.info(request, "Review season readiness before archiving.")
        return redirect("season_archive_readiness", season_pk=season.pk)

    season.is_closed = True
    season.is_active = False
    season.closed_at = timezone.now()
    season.save(update_fields=["is_closed", "is_active", "closed_at"])
    _audit_event(
        team=team,
        actor=request.user,
        action=AuditEvent.Action.UPDATED,
        obj=season,
        season=season,
        summary=f"Archived season: {season.name}",
        details={"is_closed": True, "is_active": False},
    )
    messages.success(request, f"{season.name} is now archived and protected from normal operational edits.")
    return redirect("season_review", season_pk=season.pk)

@login_required
@require_POST
def season_reopen(request, season_pk):
    if not _is_admin(request.user):
        raise PermissionDenied
    team = _team(request.user)
    season = get_object_or_404(Season, pk=season_pk, team=team)
    if not season.is_closed:
        messages.info(request, f"{season.name} is already open for editing.")
        return redirect("season_review", season_pk=season.pk)

    season.is_closed = False
    season.closed_at = None
    season.save(update_fields=["is_closed", "closed_at"])
    _audit_event(
        team=team,
        actor=request.user,
        action=AuditEvent.Action.RESTORED,
        obj=season,
        season=season,
        summary=f"Reopened archived season: {season.name}",
        details={"is_closed": False, "is_active": season.is_active},
    )
    messages.success(
        request,
        f"{season.name} reopened for corrections. It was not made the active season automatically."
    )
    return redirect("season_review", season_pk=season.pk)

@login_required
def rider_history(request, pk):
    team = _team(request.user); rider = get_object_or_404(Rider, pk=pk, team=team)
    if not _can_view_private_rider(request.user, rider):
        raise PermissionDenied
    seasons = Season.objects.filter(memberships__rider=rider).distinct().order_by("-start_date")
    history = []
    for season in seasons:
        summary_rows = _season_rider_summary(season, [rider])
        if not summary_rows:
            continue
        row = summary_rows[0]
        row["awards"] = RiderAward.objects.filter(season=season, rider=rider)
        if not _can_manage(request.user):
            row["awards"] = row["awards"].filter(published=True)
        notes = RiderDevelopmentNote.objects.filter(season=season, rider=rider).select_related("author")
        if not _can_manage(request.user):
            notes = notes.filter(family_visible=True)
        row["notes"] = notes
        row["results"] = ShowResult.objects.filter(
            entry__rider=rider,
            entry__show_class__show__season=season,
        ).select_related(
            "entry__show_class__show", "entry__show_class__season_class"
        ).order_by("-entry__show_class__show__show_date", "entry__show_class__sort_order")
        history.append(row)
    return render(request, "portal/rider_history.html", {
        "rider": rider, "history": history, "can_manage": _can_manage(request.user)
    })

@login_required
def historical_result_edit(request, result_pk):
    """Edit one rider-specific historical result without opening the whole season."""
    _require_manage(request.user)
    team = _team(request.user)
    result = get_object_or_404(
        ShowResult.objects.select_related(
            "entry__rider",
            "entry__show_class__show__season",
            "entry__show_class__season_class",
        ),
        pk=result_pk,
        entry__show_class__show__team=team,
    )
    entry = result.entry
    show = entry.show_class.show
    if not show.is_historical_import:
        raise PermissionDenied("This editor is only for historical/imported records.")

    form = HistoricalResultEditForm(
        request.POST or None,
        entry=entry,
        initial={
            "season_class": entry.show_class.season_class_id,
            "competition_track": entry.competition_track,
            "place": result.place,
            "manual_points": result.manual_points,
            "points": result.points,
            "horse_name": result.horse_name,
            "notes": result.notes,
        },
    )
    if form.is_valid():
        season_class = form.cleaned_data["season_class"]
        track = form.cleaned_data["competition_track"]

        existing = ShowEntry.objects.filter(
            show_class__show=show,
            show_class__season_class=season_class,
            rider=entry.rider,
            competition_track=track,
        ).exclude(pk=entry.pk).exists()
        if existing:
            form.add_error(
                None,
                "That rider already has a historical result for this show, class, and competition track."
            )
        else:
            with transaction.atomic():
                old_show_class = entry.show_class
                show_class, _ = ShowClass.objects.get_or_create(
                    show=show,
                    season_class=season_class,
                    defaults={
                        "name": season_class.name,
                        "discipline": season_class.discipline,
                        "sort_order": season_class.sort_order,
                    },
                )
                entry.show_class = show_class
                entry.competition_track = track
                entry.entry_type = (
                    ShowEntry.EntryType.TEAM
                    if track == ShowEntry.CompetitionTrack.TEAM
                    else ShowEntry.EntryType.INDIVIDUAL
                )
                entry.status = ShowEntry.Status.ENTERED
                entry.is_point_rider = False
                entry.save(
                    update_fields=[
                        "show_class", "competition_track", "entry_type",
                        "status", "is_point_rider"
                    ]
                )

                result.place = form.cleaned_data["place"]
                result.manual_points = form.cleaned_data["manual_points"]
                result.points = form.cleaned_data["points"]
                result.horse_name = form.cleaned_data["horse_name"]
                result.notes = form.cleaned_data["notes"]
                result.save()

                if old_show_class.pk != show_class.pk and not old_show_class.entries.exists():
                    old_show_class.delete()

                _audit_event(
                    team=team,
                    actor=request.user,
                    action=AuditEvent.Action.UPDATED,
                    obj=result,
                    season=show.season,
                    summary=f"Edited historical result: {entry.rider} · {show.name}",
                    details={
                        "rider": entry.rider,
                        "show": show,
                        "class": season_class.name,
                        "competition_track": track,
                        "place": result.place,
                        "points": result.points,
                    },
                )
            messages.success(request, "Historical result updated.")
            return redirect("rider_history", pk=entry.rider_id)

    return render(request, "portal/historical_result_edit.html", {
        "form": form,
        "result": result,
        "entry": entry,
        "show": show,
        "rider": entry.rider,
    })

@login_required
def historical_result_delete(request, result_pk):
    """Delete one rider's historical result and clean up orphaned import records."""
    _require_manage(request.user)
    team = _team(request.user)
    result = get_object_or_404(
        ShowResult.objects.select_related(
            "entry__rider",
            "entry__show_class__show__season",
        ),
        pk=result_pk,
        entry__show_class__show__team=team,
    )
    entry = result.entry
    rider = entry.rider
    show_class = entry.show_class
    show = show_class.show
    season = show.season
    show_label = show.name
    if not show.is_historical_import:
        raise PermissionDenied("This delete action is only for historical/imported records.")

    if request.method == "POST":
        with transaction.atomic():
            audit_details = {
                "rider": rider,
                "show": show,
                "class": show_class.display_name,
                "competition_track": entry.competition_track,
                "place": result.place,
                "points": result.points,
            }
            result.delete()
            entry.delete()

            if not show_class.entries.exists():
                show_class.delete()
            if not show.classes.filter(entries__isnull=False).exists():
                show.delete()

            _audit_event(
                team=team,
                actor=request.user,
                action=AuditEvent.Action.REMOVED,
                entity_type="ShowResult",
                entity_id=result_pk,
                entity_label=f"{rider} · {show_label}",
                season=season,
                summary=f"Deleted historical result: {rider} · {show_label}",
                details=audit_details,
            )

        messages.success(request, "Historical result deleted.")
        return redirect("rider_history", pk=rider.pk)

    other_rider_results = ShowResult.objects.filter(
        entry__show_class__show=show
    ).exclude(pk=result.pk).count()

    return render(request, "portal/historical_result_delete.html", {
        "result": result,
        "entry": entry,
        "show": show,
        "rider": rider,
        "other_rider_results": other_rider_results,
    })

@login_required
def historical_results_add(request, pk, season_pk=None):
    """Enter prior-season individual results without rebuilding the normal show-entry workflow."""
    _require_manage(request.user)
    team = _team(request.user)
    rider = get_object_or_404(Rider, pk=pk, team=team)

    initial = {}
    if season_pk:
        season = get_object_or_404(
            Season.objects.filter(team=team, memberships__rider=rider).distinct(),
            pk=season_pk,
        )
        initial["season"] = season

    header = HistoricalResultHeaderForm(
        request.POST or None,
        team=team,
        rider=rider,
        initial=initial,
    )

    selected_season = None
    selected_competition_level = Show.CompetitionLevel.REGULAR
    header_valid = header.is_valid() if request.method == "POST" else False
    if request.method == "POST" and header_valid:
        selected_season = header.cleaned_data["season"]
        selected_competition_level = header.cleaned_data["competition_level"]
    elif season_pk:
        selected_season = initial["season"]

    lines = HistoricalResultFormSet(
        request.POST or None,
        prefix="results",
        form_kwargs={
            "season": selected_season,
            "rider": rider,
            "competition_level": selected_competition_level,
        },
    )

    if request.method == "POST" and header_valid and lines.is_valid():
        valid_rows = [
            form.cleaned_data for form in lines
            if form.cleaned_data and not form.cleaned_data.get("DELETE")
        ]
        if not valid_rows:
            lines.non_form_errors = lambda: ["Enter at least one historical result."]
        else:
            season = header.cleaned_data["season"]
            membership = get_object_or_404(SeasonMembership, season=season, rider=rider)

            # This workflow intentionally permits archived/closed seasons.
            # Regular-season imports use the regular track; finals imports use the
            # same separate Individual/Team tracks as live Region/Zone/National shows.
            competition_level = header.cleaned_data["competition_level"]
            with transaction.atomic():
                show, created = Show.objects.get_or_create(
                    team=team,
                    season=season,
                    name=header.cleaned_data["show_name"].strip(),
                    show_date=header.cleaned_data["show_date"],
                    competition_level=competition_level,
                    is_historical_import=True,
                    defaults={
                        "venue": header.cleaned_data.get("venue", ""),
                        "status": Show.Status.COMPLETE,
                        "futures_team_place": header.cleaned_data.get("futures_team_place"),
                        "upper_team_place": header.cleaned_data.get("upper_team_place"),
                        "notes": header.cleaned_data.get("notes", ""),
                    },
                )
                if not created:
                    changed = []
                    venue = header.cleaned_data.get("venue", "")
                    notes = header.cleaned_data.get("notes", "")
                    if venue and not show.venue:
                        show.venue = venue; changed.append("venue")
                    if notes and not show.notes:
                        show.notes = notes; changed.append("notes")
                    if show.status != Show.Status.COMPLETE:
                        show.status = Show.Status.COMPLETE; changed.append("status")
                    futures_place = header.cleaned_data.get("futures_team_place")
                    upper_place = header.cleaned_data.get("upper_team_place")
                    if futures_place is not None and show.futures_team_place != futures_place:
                        show.futures_team_place = futures_place; changed.append("futures_team_place")
                    if upper_place is not None and show.upper_team_place != upper_place:
                        show.upper_team_place = upper_place; changed.append("upper_team_place")
                    if changed:
                        show.save(update_fields=changed)

                saved = 0
                for row in valid_rows:
                    season_class = row["season_class"]
                    if not membership.classes.filter(pk=season_class.pk).exists():
                        raise PermissionDenied

                    show_class, _ = ShowClass.objects.get_or_create(
                        show=show,
                        season_class=season_class,
                        defaults={
                            "name": season_class.name,
                            "discipline": season_class.discipline,
                            "sort_order": season_class.sort_order,
                        },
                    )
                    competition_track = (
                        ShowEntry.CompetitionTrack.REGULAR
                        if competition_level == Show.CompetitionLevel.REGULAR
                        else row["competition_track"]
                    )
                    entry_type = (
                        ShowEntry.EntryType.INDIVIDUAL
                        if competition_track != ShowEntry.CompetitionTrack.TEAM
                        else ShowEntry.EntryType.TEAM
                    )
                    entry, _ = ShowEntry.objects.get_or_create(
                        show_class=show_class,
                        rider=rider,
                        competition_track=competition_track,
                        defaults={
                            "entry_type": entry_type,
                            "is_point_rider": False,
                            "status": ShowEntry.Status.ENTERED,
                            "notes": "Historical result",
                        },
                    )
                    entry.entry_type = entry_type
                    entry.is_point_rider = False
                    entry.status = ShowEntry.Status.ENTERED
                    entry.save(update_fields=["entry_type", "is_point_rider", "status"])

                    points = row.get("points")
                    place = row.get("place")
                    result, _ = ShowResult.objects.get_or_create(entry=entry)
                    result.place = place
                    result.horse_name = row.get("horse_name", "")
                    result.notes = row.get("notes", "")
                    if points is not None:
                        result.points = points
                        result.manual_points = True
                    else:
                        # Let the season scoring configuration calculate points
                        # from placing when explicit historical points were omitted.
                        result.manual_points = False
                    result.save()
                    saved += 1

            _audit_event(
                team=team,
                actor=request.user,
                action=AuditEvent.Action.CREATED,
                obj=season,
                season=season,
                summary=f"Historical results entered: {rider.display_name} · {season.name}",
                details={
                    "rider_id": rider.pk,
                    "rider": rider.display_name,
                    "results_saved": saved,
                    "show_name": header.cleaned_data["show_name"].strip(),
                    "competition_level": competition_level,
                },
            )
            messages.success(
                request,
                f"{saved} historical result{'s' if saved != 1 else ''} saved for "
                f"{rider.display_name} · {season.name}."
            )
            return redirect("rider_history", pk=rider.pk)

    return render(request, "portal/historical_results_form.html", {
        "rider": rider,
        "header": header,
        "lines": lines,
        "selected_season": selected_season,
        "selected_competition_level": selected_competition_level,
    })

@login_required
def rider_summary_print(request, pk, season_pk):
    team = _team(request.user); rider = get_object_or_404(Rider, pk=pk, team=team)
    if not _can_view_private_rider(request.user, rider):
        raise PermissionDenied
    season = get_object_or_404(Season, pk=season_pk, team=team)
    summary = _season_rider_summary(season, [rider])[0]
    qualifications = [r for r in _qualification_rows(season) if r["rider"].pk == rider.pk]
    awards = RiderAward.objects.filter(season=season, rider=rider, published=True)
    notes = RiderDevelopmentNote.objects.filter(season=season, rider=rider, family_visible=True).select_related("author")
    postseason_results = ShowResult.objects.filter(
        entry__rider=rider,
        entry__show_class__show__season=season,
        entry__show_class__show__competition_level__in=[
            Show.CompetitionLevel.REGIONAL,
            Show.CompetitionLevel.ZONE,
            Show.CompetitionLevel.NATIONAL,
        ],
    ).select_related(
        "entry__show_class__show", "entry__show_class__season_class"
    ).order_by("entry__show_class__show__show_date", "entry__show_class__sort_order")
    return render(request, "portal/rider_summary_print.html", {
        "rider": rider, "season": season, "summary": summary,
        "qualifications": qualifications, "awards": awards, "notes": notes,
        "postseason_results": postseason_results,
    })

@login_required
def development_note_add(request, pk, season_pk):
    _require_manage(request.user); team = _team(request.user)
    rider = get_object_or_404(Rider, pk=pk, team=team); season = get_object_or_404(Season, pk=season_pk, team=team)
    form = RiderDevelopmentNoteForm(request.POST or None)
    if form.is_valid():
        obj = form.save(commit=False); obj.rider = rider; obj.season = season; obj.author = request.user; obj.save()
        messages.success(request, "Development note added."); return redirect("rider_history", pk=rider.pk)
    return render(request, "portal/form.html", {"form": form, "title": f"Development note · {rider.display_name}", "eyebrow": season.name})

@login_required
def award_list(request, season_pk):
    team = _team(request.user); season = get_object_or_404(Season, pk=season_pk, team=team)
    awards = RiderAward.objects.filter(season=season).select_related("rider")
    if not _can_manage(request.user):
        awards = awards.filter(published=True, rider__in=_visible_riders(request.user, team))
    return render(request, "portal/award_list.html", {"season": season, "awards": awards, "can_manage": _can_manage(request.user)})

@login_required
@friendly_integrity_errors
def award_add(request, season_pk):
    _require_manage(request.user); team = _team(request.user); season = get_object_or_404(Season, pk=season_pk, team=team)
    form = RiderAwardForm(request.POST or None, season=season)
    if form.is_valid():
        obj = form.save(commit=False); obj.season = season; obj.created_by = request.user; obj.save()
        messages.success(request, "Award added."); return redirect("award_list", season_pk=season.pk)
    return render(request, "portal/form.html", {"form": form, "title": "Add award or recognition", "eyebrow": season.name})

@login_required
def team_record_book(request):
    team = _team(request.user)

    grouped = list(
        ShowResult.objects.filter(
            entry__rider__team=team,
            entry__show_class__show__competition_level=Show.CompetitionLevel.REGULAR,
            entry__competition_track=ShowEntry.CompetitionTrack.REGULAR,
            entry__show_class__season_class__isnull=False,
            entry__status__in=[ShowEntry.Status.PLANNED, ShowEntry.Status.ENTERED],
        )
        .values(
            "entry__rider_id",
            "entry__show_class__show__season_id",
            "entry__show_class__season_class_id",
        )
        .annotate(
            points=Sum("points"),
            wins=Count("id", filter=Q(place=1)),
        )
    )

    rider_ids = {row["entry__rider_id"] for row in grouped}
    season_ids = {row["entry__show_class__show__season_id"] for row in grouped}
    class_ids = {row["entry__show_class__season_class_id"] for row in grouped}
    riders = Rider.objects.in_bulk(rider_ids)
    seasons = Season.objects.in_bulk(season_ids)
    season_classes = SeasonClass.objects.in_bulk(class_ids)

    records = []
    for row in grouped:
        rider = riders.get(row["entry__rider_id"])
        season = seasons.get(row["entry__show_class__show__season_id"])
        season_class = season_classes.get(row["entry__show_class__season_class_id"])
        if not rider or not season or not season_class:
            continue
        points = row["points"] or 0
        wins = row["wins"] or 0
        if points or wins:
            records.append({
                "season": season,
                "rider": rider,
                "season_class": season_class,
                "points": points,
                "wins": wins,
            })

    records.sort(key=lambda x: (x["points"], x["wins"]), reverse=True)
    awards = RiderAward.objects.filter(
        season__team=team, published=True
    ).select_related("season", "rider")[:50]
    postseason_entries = ShowEntry.objects.filter(
        show_class__show__team=team,
        competition_track=ShowEntry.CompetitionTrack.INDIVIDUAL,
        result__isnull=False,
    )
    finals_counts = {
        "regional": postseason_entries.filter(
            show_class__show__competition_level=Show.CompetitionLevel.REGIONAL
        ).values("rider_id").distinct().count(),
        "zone": postseason_entries.filter(
            show_class__show__competition_level=Show.CompetitionLevel.ZONE
        ).values("rider_id").distinct().count(),
        "national": postseason_entries.filter(
            show_class__show__competition_level=Show.CompetitionLevel.NATIONAL
        ).values("rider_id").distinct().count(),
    }
    return render(request, "portal/team_record_book.html", {
        "records": records[:25],
        "awards": awards,
        "finals_counts": finals_counts,
    })
