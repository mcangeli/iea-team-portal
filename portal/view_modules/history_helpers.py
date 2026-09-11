"""Private helpers for the history view domain."""

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


def _season_rider_summary(season, riders):
    riders = list(riders)
    if not riders:
        return []

    rider_ids = [rider.pk for rider in riders]
    memberships = {
        membership.rider_id: membership
        for membership in SeasonMembership.objects.filter(
            season=season, rider_id__in=rider_ids
        ).prefetch_related("classes")
    }

    regular_totals = {}
    for row in ShowResult.objects.filter(
        entry__rider_id__in=rider_ids,
        entry__show_class__show__season=season,
        entry__show_class__show__competition_level=Show.CompetitionLevel.REGULAR,
        entry__competition_track=ShowEntry.CompetitionTrack.REGULAR,
        entry__show_class__season_class__isnull=False,
        entry__status__in=[ShowEntry.Status.PLANNED, ShowEntry.Status.ENTERED],
    ).values(
        "entry__rider_id",
        "entry__show_class__season_class_id",
    ).annotate(
        points=Sum("points"),
        wins=Count("id", filter=Q(place=1)),
    ):
        regular_totals[
            (row["entry__rider_id"], row["entry__show_class__season_class_id"])
        ] = {
            "points": row["points"] or 0,
            "wins": row["wins"] or 0,
        }

    show_counts = {
        row["rider_id"]: row["count"]
        for row in ShowEntry.objects.filter(
            rider_id__in=rider_ids,
            show_class__show__season=season,
        ).values("rider_id").annotate(
            count=Count("show_class__show_id", distinct=True)
        )
    }
    win_counts = {
        row["entry__rider_id"]: row["count"]
        for row in ShowResult.objects.filter(
            entry__rider_id__in=rider_ids,
            entry__show_class__show__season=season,
            place=1,
        ).values("entry__rider_id").annotate(count=Count("id"))
    }
    attendance_counts = {
        row["rider_id"]: row["count"]
        for row in LessonAttendance.objects.filter(
            rider_id__in=rider_ids,
            lesson__season=season,
            status=LessonAttendance.Status.PRESENT,
        ).values("rider_id").annotate(count=Count("id"))
    }
    volunteer_totals = {
        row["rider_id"]: row["total"] or 0
        for row in VolunteerLog.objects.filter(
            rider_id__in=rider_ids,
            season=season,
            status=VolunteerLog.Status.APPROVED,
        ).values("rider_id").annotate(total=Sum("hours"))
    }

    rows = []
    for rider in riders:
        membership = memberships.get(rider.pk)
        class_points = []
        if membership:
            for season_class in sorted(
                membership.classes.all(),
                key=lambda sc: (sc.sort_order, sc.name.casefold()),
            ):
                totals = regular_totals.get((rider.pk, season_class.pk), {})
                class_points.append({
                    "season_class": season_class,
                    "points": totals.get("points", 0),
                    "wins": totals.get("wins", 0),
                })

        rows.append({
            "rider": rider,
            "membership": membership,
            "class_points": class_points,
            "shows": show_counts.get(rider.pk, 0),
            "wins": win_counts.get(rider.pk, 0),
            "attendance": attendance_counts.get(rider.pk, 0),
            "volunteer_hours": volunteer_totals.get(rider.pk, 0),
        })
    return rows

def _history_import_norm(value):
    return " ".join((value or "").strip().casefold().split())

def _history_import_date(value):
    raw = (value or "").strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValidationError("Use YYYY-MM-DD or MM/DD/YYYY for show_date.")

def _history_import_int(value, *, label, minimum=1):
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        parsed = int(raw)
    except ValueError:
        raise ValidationError(f"{label} must be a whole number.")
    if parsed < minimum or parsed > 999:
        raise ValidationError(f"{label} must be between {minimum} and 999.")
    return parsed

def _history_import_decimal(value):
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        parsed = Decimal(raw)
    except Exception:
        raise ValidationError("Points must be a number.")
    if parsed < 0 or parsed > Decimal("999.9"):
        raise ValidationError("Points must be between 0 and 999.9.")
    return parsed.quantize(Decimal("0.1"))

def _history_import_level(value):
    raw = _history_import_norm(value)
    aliases = {
        "regular": Show.CompetitionLevel.REGULAR,
        "regular season": Show.CompetitionLevel.REGULAR,
        "regional": Show.CompetitionLevel.REGIONAL,
        "region": Show.CompetitionLevel.REGIONAL,
        "region finals": Show.CompetitionLevel.REGIONAL,
        "zone": Show.CompetitionLevel.ZONE,
        "zones": Show.CompetitionLevel.ZONE,
        "zone finals": Show.CompetitionLevel.ZONE,
        "national": Show.CompetitionLevel.NATIONAL,
        "nationals": Show.CompetitionLevel.NATIONAL,
        "national finals": Show.CompetitionLevel.NATIONAL,
    }
    if raw not in aliases:
        raise ValidationError("competition_level must be regular, regional, zone, or national.")
    return aliases[raw]

def _history_import_track(value, competition_level):
    if competition_level == Show.CompetitionLevel.REGULAR:
        return ShowEntry.CompetitionTrack.REGULAR
    raw = _history_import_norm(value)
    aliases = {
        "individual": ShowEntry.CompetitionTrack.INDIVIDUAL,
        "ind": ShowEntry.CompetitionTrack.INDIVIDUAL,
        "team": ShowEntry.CompetitionTrack.TEAM,
    }
    if raw not in aliases:
        raise ValidationError("Finals rows require competition_track of individual or team.")
    return aliases[raw]

def _accessiea_show_column(header):
    """Parse an AccessIEA Rider Performance show column into show metadata."""
    raw = (header or "").strip()
    match = re.match(r"^(?P<date>\d{1,2}/\d{1,2}/\d{4})\s+(?P<name>.+)$", raw)
    if not match:
        return None

    show_date = datetime.strptime(match.group("date"), "%m/%d/%Y").date()
    name = match.group("name").strip()
    lowered = name.casefold()

    competition_level = Show.CompetitionLevel.REGULAR
    track = ShowEntry.CompetitionTrack.REGULAR

    if "national" in lowered and "final" in lowered:
        competition_level = Show.CompetitionLevel.NATIONAL
    elif "region" in lowered and "final" in lowered:
        competition_level = Show.CompetitionLevel.REGIONAL
    elif "zone" in lowered and "final" in lowered:
        competition_level = Show.CompetitionLevel.ZONE

    if competition_level != Show.CompetitionLevel.REGULAR:
        if re.search(r"\bteam\s*$", name, re.IGNORECASE):
            track = ShowEntry.CompetitionTrack.TEAM
            name = re.sub(r"\s+team\s*$", "", name, flags=re.IGNORECASE).strip()
        elif re.search(r"\bindividual\s*$", name, re.IGNORECASE):
            track = ShowEntry.CompetitionTrack.INDIVIDUAL
            name = re.sub(r"\s+individual\s*$", "", name, flags=re.IGNORECASE).strip()
        else:
            track = ShowEntry.CompetitionTrack.INDIVIDUAL

    return {
        "show_date": show_date,
        "show_name": name[:180],
        "competition_level": competition_level,
        "competition_track": track,
    }

def _accessiea_team_level(class_name, rider=None):
    """Infer a squad only when the AccessIEA class name makes it explicit."""
    name = _history_import_norm(class_name)
    if any(token in name for token in ("varsity", "junior varsity", " jv ")):
        return SeasonMembership.TeamLevel.UPPER
    if name.startswith("jv "):
        return SeasonMembership.TeamLevel.UPPER
    if "future" in name:
        return SeasonMembership.TeamLevel.FUTURES
    if rider and rider.grade:
        if 4 <= rider.grade <= 8:
            return SeasonMembership.TeamLevel.FUTURES
        if 9 <= rider.grade <= 12:
            return SeasonMembership.TeamLevel.UPPER
    return ""

def _accessiea_split_name(full_name):
    parts = [part for part in (full_name or "").strip().split() if part]
    if len(parts) < 2:
        return "", ""
    # Preserve multi-word given names better than treating every token after the
    # first as the surname. The full AccessIEA display name remains visible in
    # preview so managers can catch unusual compound-surname cases before commit.
    return " ".join(parts[:-1]), parts[-1]

def _historical_import_preview_accessiea(season, text, bootstrap_missing=False):
    reader = csv.DictReader(text.splitlines())
    if not reader.fieldnames:
        raise ValidationError("The AccessIEA CSV does not contain a header row.")

    normalized_field_map = {
        _history_import_norm(header).replace("\ufeff", ""): header
        for header in reader.fieldnames
    }
    required_labels = ["#IEA", "# of Shows", "Rider Name", "Class", "Total Rider Points"]
    missing = [
        label for label in required_labels
        if _history_import_norm(label) not in normalized_field_map
    ]
    if missing:
        raise ValidationError(
            "This looks like an AccessIEA Rider Performance export but is missing: "
            + ", ".join(missing)
        )

    iea_field = normalized_field_map[_history_import_norm("#IEA")]
    shows_field = normalized_field_map[_history_import_norm("# of Shows")]
    rider_field = normalized_field_map[_history_import_norm("Rider Name")]
    class_field = normalized_field_map[_history_import_norm("Class")]
    total_points_field = normalized_field_map[_history_import_norm("Total Rider Points")]

    show_columns = []
    for header in reader.fieldnames:
        parsed = _accessiea_show_column(header)
        if parsed:
            parsed["header"] = header
            show_columns.append(parsed)
    if not show_columns:
        raise ValidationError("No dated show columns were found in the AccessIEA export.")

    team_riders = list(season.team.riders.all())
    rider_by_iea = {}
    rider_by_name = {}
    ambiguous_names = set()
    for rider in team_riders:
        member_number = (rider.iea_member_number or "").strip()
        if member_number:
            rider_by_iea[member_number] = rider
        names = {_history_import_norm(f"{rider.first_name} {rider.last_name}")}
        if rider.preferred_name:
            names.add(_history_import_norm(f"{rider.preferred_name} {rider.last_name}"))
        for name in names:
            if name in rider_by_name and rider_by_name[name].pk != rider.pk:
                ambiguous_names.add(name)
            else:
                rider_by_name[name] = rider

    season_memberships = {
        m.rider_id: m
        for m in season.memberships.select_related("rider").prefetch_related("classes")
    }
    season_classes = list(season.season_classes.all())
    class_map = {}
    for season_class in season_classes:
        class_map.setdefault(_history_import_norm(season_class.name), []).append(season_class)

    rows = []
    seen_keys = set()
    source_bootstrap = {}

    for source_row, source in enumerate(reader, start=2):
        if source_row > 1001:
            raise ValidationError("Historical imports are limited to 1,000 source rows per file.")
        if not any(str(v or "").strip() for v in source.values()):
            continue

        source_iea = (source.get(iea_field) or "").strip()
        source_name = (source.get(rider_field) or "").strip()
        source_class = (source.get(class_field) or "").strip()
        name_key = _history_import_norm(source_name)
        first_name, last_name = _accessiea_split_name(source_name)

        rider = rider_by_iea.get(source_iea) if source_iea else None
        match_note = ""
        if rider:
            legal_key = _history_import_norm(f"{rider.first_name} {rider.last_name}")
            preferred_key = (
                _history_import_norm(f"{rider.preferred_name} {rider.last_name}")
                if rider.preferred_name else ""
            )
            if name_key and name_key not in {legal_key, preferred_key}:
                match_note = "AccessIEA rider name differs from portal; matched by #IEA."
        elif name_key and name_key not in ambiguous_names:
            rider = rider_by_name.get(name_key)
            if rider:
                if source_iea and rider.iea_member_number and rider.iea_member_number != source_iea:
                    rider = None
                elif source_iea and not rider.iea_member_number:
                    match_note = "Existing rider matched by exact name; #IEA will be added on commit."
                else:
                    match_note = "Existing rider matched by exact name."

        proposed_new_rider = rider is None
        rider_error = ""
        if proposed_new_rider:
            if not bootstrap_missing:
                rider_error = (
                    f"Rider #{source_iea} ({source_name}) was not found on this season roster."
                    if source_iea else f"Rider {source_name or '—'} was not found on this season roster."
                )
            elif not source_iea:
                rider_error = "A new rider cannot be created without an AccessIEA #IEA member number."
            elif not first_name or not last_name:
                rider_error = "A new rider requires a first and last name."
            elif name_key in ambiguous_names:
                rider_error = "Rider name is ambiguous and #IEA did not match an existing rider."

        membership = season_memberships.get(rider.pk) if rider else None
        team_level = membership.team_level if membership else _accessiea_team_level(source_class, rider)
        if not team_level and bootstrap_missing and not rider_error:
            rider_error = (
                "Could not determine Futures vs Upper School from this class/rider. "
                "Create the rider or season membership manually, then preview again."
            )

        class_matches = class_map.get(_history_import_norm(source_class), [])
        compatible_classes = [
            c for c in class_matches
            if c.team_level in {team_level, SeasonClass.TeamLevel.BOTH}
        ] if team_level else []

        season_class = compatible_classes[0] if len(compatible_classes) == 1 else None
        proposed_new_class = False
        proposed_assign_class = False
        class_error = ""

        if not source_class:
            class_error = "Class name is required."
        elif len(compatible_classes) > 1:
            class_error = "Class name matches more than one compatible season class."
        elif season_class:
            if membership and not membership.classes.filter(pk=season_class.pk).exists():
                if bootstrap_missing:
                    proposed_assign_class = True
                else:
                    class_error = "Class is not assigned to this rider for the season."
        elif bootstrap_missing and team_level:
            proposed_new_class = True
            proposed_assign_class = True
        elif not rider_error:
            class_error = "AccessIEA class is not assigned to this rider in the selected season."

        source_key = source_iea or name_key
        source_bootstrap.setdefault(source_key, {
            "source_iea": source_iea,
            "source_name": source_name,
            "first_name": first_name,
            "last_name": last_name,
            "rider_id": rider.pk if rider else None,
            "create_rider": proposed_new_rider and not rider_error,
            "create_membership": (membership is None and not rider_error),
            "team_level": team_level,
            "set_iea_number": bool(
                rider and source_iea and not rider.iea_member_number and not rider_error
            ),
        })

        nonblank_show_count = sum(
            1 for col in show_columns if (source.get(col["header"]) or "").strip() != ""
        )
        try:
            reported_show_count = int((source.get(shows_field) or "0").strip() or "0")
        except ValueError:
            reported_show_count = None

        source_points = []
        generated_start = len(rows)

        for col in show_columns:
            raw = (source.get(col["header"]) or "").strip()
            if raw == "":
                continue

            errors = []
            warnings = []
            actions = []
            if match_note:
                warnings.append(match_note)
            if rider_error:
                errors.append(rider_error)
            if class_error:
                errors.append(class_error)

            if proposed_new_rider and not rider_error:
                actions.append(f"Create rider {source_name} (#{source_iea}).")
            elif rider and source_iea and not rider.iea_member_number:
                actions.append(f"Add #IEA {source_iea} to existing rider {rider}.")
            if membership is None and not rider_error:
                actions.append(
                    f"Add {source_name} to {season.name} as "
                    f"{'Futures' if team_level == SeasonMembership.TeamLevel.FUTURES else 'Upper School'}."
                )
            if proposed_new_class and not class_error:
                actions.append(
                    f"Create season class {source_class} for "
                    f"{'Futures' if team_level == SeasonMembership.TeamLevel.FUTURES else 'Upper School'}."
                )
            if proposed_assign_class and not class_error:
                actions.append(f"Assign {source_class} to {source_name} for this season.")

            try:
                points = _history_import_decimal(raw)
            except ValidationError as exc:
                errors.extend(exc.messages)
                points = None
            if points is not None:
                source_points.append(points)

            if (
                col["competition_track"] == ShowEntry.CompetitionTrack.TEAM
                and source_class
            ):
                code = source_class.strip().upper()
                if code.startswith("H8 ") or code.startswith("H14 ") or code in {"H8", "H14"}:
                    errors.append("H8 and H14 Walk/Trot are individual-only.")

            if col["show_date"] < season.start_date or col["show_date"] > season.end_date:
                warnings.append("Show date falls outside the selected season dates.")

            logical_rider_key = rider.pk if rider else f"new:{source_iea}:{name_key}"
            logical_class_key = (
                season_class.pk if season_class
                else f"new:{team_level}:{_history_import_norm(source_class)}"
            )
            row_key = (
                _history_import_norm(col["show_name"]),
                col["show_date"].isoformat(),
                col["competition_level"],
                logical_rider_key,
                logical_class_key,
                col["competition_track"],
            )
            if row_key in seen_keys:
                errors.append("Duplicate result appears more than once in this AccessIEA export.")
            seen_keys.add(row_key)

            existing_result = None
            if not errors and rider and season_class:
                existing_result = ShowResult.objects.filter(
                    entry__show_class__show__season=season,
                    entry__show_class__show__name__iexact=col["show_name"],
                    entry__show_class__show__show_date=col["show_date"],
                    entry__show_class__show__competition_level=col["competition_level"],
                    entry__rider_id=rider.pk,
                    entry__show_class__season_class_id=season_class.pk,
                    entry__competition_track=col["competition_track"],
                ).first()
                if existing_result:
                    warnings.append("Matching result already exists and will be skipped.")

            rows.append({
                "row_number": source_row,
                "source_format": "AccessIEA Rider Performance",
                "source_iea": source_iea,
                "source_name": source_name,
                "rider_id": rider.pk if rider else None,
                "rider_name": str(rider) if rider else source_name,
                "first_name": first_name,
                "last_name": last_name,
                "create_rider": proposed_new_rider and not rider_error,
                "create_membership": membership is None and not rider_error,
                "set_iea_number": bool(rider and source_iea and not rider.iea_member_number and not rider_error),
                "team_level": team_level,
                "season_class_id": season_class.pk if season_class else None,
                "season_class_name": season_class.name if season_class else source_class,
                "create_class": proposed_new_class and not class_error,
                "assign_class": proposed_assign_class and not class_error,
                "show_name": col["show_name"],
                "show_date": col["show_date"].isoformat(),
                "competition_level": col["competition_level"],
                "competition_track": col["competition_track"],
                "place": None,
                "points": str(points) if points is not None else "",
                "horse_name": "",
                "venue": "",
                "notes": "Imported from AccessIEA Rider Performance export",
                "futures_team_place": None,
                "upper_team_place": None,
                "bootstrap_actions": actions if len(rows) == generated_start else [],
                "duplicate": bool(existing_result),
                "errors": errors,
                "warnings": warnings,
                "ready": not errors and not existing_result,
            })

        try:
            reported_total = _history_import_decimal(source.get(total_points_field))
        except ValidationError:
            reported_total = None
        calculated_total = sum(source_points, Decimal("0"))
        if reported_total is not None and calculated_total != reported_total and len(rows) > generated_start:
            rows[generated_start]["warnings"].append(
                f"Show-column points total {calculated_total} does not match "
                f"AccessIEA Total Rider Points {reported_total}."
            )

        if reported_show_count is not None and nonblank_show_count != reported_show_count and len(rows) > generated_start:
            rows[generated_start]["warnings"].append(
                f"Found {nonblank_show_count} populated show columns but AccessIEA reports "
                f"{reported_show_count} shows."
            )

    if not rows:
        raise ValidationError("The AccessIEA export does not contain any populated show results.")

    return rows

def _historical_import_preview(season, upload, bootstrap_missing=False):
    try:
        text = upload.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValidationError("The CSV must be UTF-8 encoded.")

    probe = csv.reader(text.splitlines())
    try:
        headers = next(probe)
    except StopIteration:
        raise ValidationError("The CSV is empty.")

    # AccessIEA exports have historically varied slightly in spacing/case, so
    # normalize the fixed metadata headers before deciding which parser to use.
    normalized_headers = {
        _history_import_norm(header).replace("\ufeff", "") for header in headers
    }
    accessiea_required = {
        _history_import_norm("#IEA"),
        _history_import_norm("# of Shows"),
        _history_import_norm("Rider Name"),
        _history_import_norm("Class"),
        _history_import_norm("Total Rider Points"),
    }

    # Treat files containing the AccessIEA identity columns as AccessIEA even if
    # one of the ancillary fixed headers has a minor formatting difference. The
    # AccessIEA parser will then report a specific missing-header error rather
    # than incorrectly falling through to the portal-template parser.
    accessiea_identity = {
        _history_import_norm("#IEA"),
        _history_import_norm("Rider Name"),
        _history_import_norm("Class"),
    }

    if accessiea_required.issubset(normalized_headers) or accessiea_identity.issubset(normalized_headers):
        return _historical_import_preview_accessiea(season, text, bootstrap_missing=bootstrap_missing)

    # Re-wrap the already-decoded text for the generic importer.
    class _TextUpload:
        def read(self):
            return text.encode("utf-8")

    return _historical_import_preview_standard(season, _TextUpload())

def _historical_import_preview_standard(season, upload):
    try:
        text = upload.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValidationError("The CSV must be UTF-8 encoded.")

    reader = csv.DictReader(text.splitlines())
    if not reader.fieldnames:
        raise ValidationError("The CSV does not contain a header row.")

    headers = reader.fieldnames
    if len(headers) != len(set(headers)):
        raise ValidationError("The CSV contains duplicate column names.")
    missing = [h for h in HISTORICAL_IMPORT_HEADERS if h not in headers]
    if missing:
        raise ValidationError("Missing required column(s): " + ", ".join(missing))

    memberships = list(
        season.memberships.select_related("rider").prefetch_related("classes")
    )
    rider_name_map = {}
    ambiguous_riders = set()
    for membership in memberships:
        rider = membership.rider
        names = {
            _history_import_norm(f"{rider.first_name} {rider.last_name}"),
        }
        if rider.preferred_name:
            names.add(_history_import_norm(f"{rider.preferred_name} {rider.last_name}"))
        for name in names:
            if name in rider_name_map and rider_name_map[name].rider_id != rider.pk:
                ambiguous_riders.add(name)
            else:
                rider_name_map[name] = membership

    rows = []
    seen_keys = set()
    show_metadata = {}

    for row_number, source in enumerate(reader, start=2):
        if row_number > 1001:
            raise ValidationError("Historical imports are limited to 1,000 data rows per file.")
        if not any(str(value or "").strip() for value in source.values()):
            continue

        errors = []
        warnings = []
        parsed = {"row_number": row_number}

        rider_key = _history_import_norm(
            f"{source.get('rider_first_name', '')} {source.get('rider_last_name', '')}"
        )
        membership = None
        if not rider_key:
            errors.append("Rider first and last name are required.")
        elif rider_key in ambiguous_riders:
            errors.append("Rider name matches more than one season rider; use an unambiguous name.")
        else:
            membership = rider_name_map.get(rider_key)
            if not membership:
                errors.append("Rider was not found on this season roster.")

        show_name = (source.get("show_name") or "").strip()
        if not show_name:
            errors.append("Show name is required.")
        parsed["show_name"] = show_name[:180]

        try:
            show_date = _history_import_date(source.get("show_date"))
            parsed["show_date"] = show_date.isoformat()
            if show_date < season.start_date or show_date > season.end_date:
                warnings.append("Show date falls outside the season start/end dates.")
        except ValidationError as exc:
            errors.extend(exc.messages)
            show_date = None
            parsed["show_date"] = ""

        try:
            competition_level = _history_import_level(source.get("competition_level"))
            parsed["competition_level"] = competition_level
        except ValidationError as exc:
            errors.extend(exc.messages)
            competition_level = None
            parsed["competition_level"] = ""

        try:
            track = _history_import_track(source.get("competition_track"), competition_level)
            parsed["competition_track"] = track
        except ValidationError as exc:
            errors.extend(exc.messages)
            track = None
            parsed["competition_track"] = ""

        class_name = (source.get("class_name") or "").strip()
        parsed["class_name"] = class_name
        season_class = None
        if not class_name:
            errors.append("Class name is required.")
        elif membership:
            class_matches = [
                c for c in membership.classes.all()
                if _history_import_norm(c.name) == _history_import_norm(class_name)
            ]
            if len(class_matches) == 1:
                season_class = class_matches[0]
            elif len(class_matches) > 1:
                errors.append("Class name matches more than one assigned season class.")
            else:
                errors.append("Class is not assigned to this rider for the season.")

        try:
            place = _history_import_int(source.get("place"), label="Place")
            parsed["place"] = place
        except ValidationError as exc:
            errors.extend(exc.messages)
            place = None
            parsed["place"] = None

        try:
            points = _history_import_decimal(source.get("points"))
            parsed["points"] = str(points) if points is not None else ""
        except ValidationError as exc:
            errors.extend(exc.messages)
            points = None
            parsed["points"] = ""

        if place is None and points is None:
            errors.append("Enter a placing, points, or both.")

        horse_name = (source.get("horse_name") or "").strip()[:100]
        venue = (source.get("venue") or "").strip()[:180]
        notes = (source.get("notes") or "").strip()[:255]
        parsed.update({"horse_name": horse_name, "venue": venue, "notes": notes})

        try:
            futures_place = _history_import_int(
                source.get("futures_team_place"),
                label="Futures team place",
            )
            upper_place = _history_import_int(
                source.get("upper_team_place"),
                label="Upper team place",
            )
            parsed["futures_team_place"] = futures_place
            parsed["upper_team_place"] = upper_place
        except ValidationError as exc:
            errors.extend(exc.messages)
            parsed["futures_team_place"] = None
            parsed["upper_team_place"] = None

        if (
            competition_level == Show.CompetitionLevel.REGULAR
            and (parsed["futures_team_place"] is not None or parsed["upper_team_place"] is not None)
        ):
            warnings.append("Team placing fields are ignored for regular-season rows.")

        if (
            competition_level != Show.CompetitionLevel.REGULAR
            and track == ShowEntry.CompetitionTrack.TEAM
            and season_class
        ):
            code = (season_class.name or "").strip().upper()
            if code.startswith("H8 ") or code.startswith("H14 ") or code in {"H8", "H14"}:
                errors.append("H8 and H14 Walk/Trot are individual-only.")

        parsed["rider_id"] = membership.rider_id if membership else None
        parsed["rider_name"] = str(membership.rider) if membership else (
            f"{source.get('rider_first_name', '')} {source.get('rider_last_name', '')}".strip()
        )
        parsed["season_class_id"] = season_class.pk if season_class else None
        parsed["season_class_name"] = season_class.name if season_class else class_name

        show_key = None
        if show_name and show_date and competition_level:
            show_key = (
                _history_import_norm(show_name),
                show_date.isoformat(),
                competition_level,
            )
            metadata = {
                "venue": venue,
                "futures_team_place": parsed["futures_team_place"],
                "upper_team_place": parsed["upper_team_place"],
            }
            if show_key in show_metadata:
                existing_metadata = show_metadata[show_key]
                for field, incoming in metadata.items():
                    existing = existing_metadata.get(field)
                    if incoming not in ("", None) and existing not in ("", None) and incoming != existing:
                        errors.append(
                            f"Show {field.replace('_', ' ')} conflicts with another row for the same show."
                        )
                    elif existing in ("", None) and incoming not in ("", None):
                        existing_metadata[field] = incoming
            else:
                show_metadata[show_key] = metadata

        row_key = None
        if show_key and membership and season_class and track:
            row_key = show_key + (membership.rider_id, season_class.pk, track)
            if row_key in seen_keys:
                errors.append("Duplicate row appears earlier in this CSV.")
            seen_keys.add(row_key)

        existing_result = None
        if not errors and show_key:
            existing_result = ShowResult.objects.filter(
                entry__show_class__show__season=season,
                entry__show_class__show__name__iexact=show_name,
                entry__show_class__show__show_date=show_date,
                entry__show_class__show__competition_level=competition_level,
                entry__rider_id=membership.rider_id,
                entry__show_class__season_class_id=season_class.pk,
                entry__competition_track=track,
            ).first()
            if existing_result:
                warnings.append("Matching result already exists and will be skipped.")

        parsed["duplicate"] = bool(existing_result)
        parsed["errors"] = errors
        parsed["warnings"] = warnings
        parsed["ready"] = not errors and not existing_result
        rows.append(parsed)

    if not rows:
        raise ValidationError("The CSV does not contain any data rows.")

    return rows

def _historical_import_commit(season, rows):
    stats = {
        "results_created": 0,
        "duplicates_skipped": 0,
        "shows_touched": 0,
        "riders_created": 0,
        "memberships_created": 0,
        "classes_created": 0,
        "class_assignments_created": 0,
        "iea_numbers_added": 0,
    }
    touched_shows = set()
    rider_cache = {}
    class_cache = {}

    with transaction.atomic():
        for row in rows:
            if row.get("errors"):
                raise ValidationError(
                    "The import contains validation errors and cannot be committed."
                )
            if row.get("duplicate"):
                stats["duplicates_skipped"] += 1
                continue

            source_iea = (row.get("source_iea") or "").strip()
            source_name = (row.get("source_name") or row.get("rider_name") or "").strip()
            rider_key = row.get("rider_id") or f"{source_iea}:{_history_import_norm(source_name)}"

            rider = rider_cache.get(rider_key)
            if not rider:
                if row.get("rider_id"):
                    rider = get_object_or_404(
                        Rider, pk=row["rider_id"], team=season.team
                    )
                elif row.get("create_rider"):
                    rider = None
                    if source_iea:
                        rider = Rider.objects.filter(
                            team=season.team, iea_member_number=source_iea
                        ).first()
                    if not rider and source_name:
                        first_name = row.get("first_name") or ""
                        last_name = row.get("last_name") or ""
                        rider = Rider.objects.filter(
                            team=season.team,
                            first_name__iexact=first_name,
                            last_name__iexact=last_name,
                        ).first()
                    if not rider:
                        rider = Rider.objects.create(
                            team=season.team,
                            first_name=row.get("first_name") or "",
                            last_name=row.get("last_name") or "",
                            iea_member_number=source_iea,
                            active=True,
                        )
                        stats["riders_created"] += 1
                else:
                    raise ValidationError(
                        f"Rider {source_name or source_iea} could not be resolved during import."
                    )
                rider_cache[rider_key] = rider

            if row.get("set_iea_number") and source_iea and not rider.iea_member_number:
                conflict = Rider.objects.filter(
                    team=season.team, iea_member_number=source_iea
                ).exclude(pk=rider.pk).exists()
                if conflict:
                    raise ValidationError(
                        f"IEA member number {source_iea} is now assigned to another rider."
                    )
                rider.iea_member_number = source_iea
                rider.save(update_fields=["iea_member_number"])
                stats["iea_numbers_added"] += 1

            membership = SeasonMembership.objects.filter(
                season=season, rider=rider
            ).prefetch_related("classes").first()
            if not membership:
                team_level = row.get("team_level") or ""
                if team_level not in {
                    SeasonMembership.TeamLevel.FUTURES,
                    SeasonMembership.TeamLevel.UPPER,
                }:
                    raise ValidationError(
                        f"Team level for {rider} could not be resolved during import."
                    )
                membership = SeasonMembership.objects.create(
                    season=season,
                    rider=rider,
                    team_level=team_level,
                    notes="Created from AccessIEA historical import",
                )
                stats["memberships_created"] += 1
            elif row.get("team_level") and membership.team_level and (
                membership.team_level != row["team_level"]
            ):
                raise ValidationError(
                    f"{rider} is now assigned to a different team level for {season.name}."
                )

            class_key = row.get("season_class_id") or (
                f"{row.get('team_level')}:{_history_import_norm(row.get('season_class_name'))}"
            )
            season_class = class_cache.get(class_key)
            if not season_class:
                if row.get("season_class_id"):
                    season_class = get_object_or_404(
                        SeasonClass,
                        pk=row["season_class_id"],
                        season=season,
                    )
                elif row.get("create_class"):
                    team_level = row.get("team_level")
                    class_name = (row.get("season_class_name") or "").strip()
                    season_class = SeasonClass.objects.filter(
                        season=season,
                        name__iexact=class_name,
                        team_level__in=[team_level, SeasonClass.TeamLevel.BOTH],
                    ).first()
                    if not season_class:
                        discipline = (
                            season.team.discipline
                            if season.team.discipline != "multi"
                            else "other"
                        )
                        season_class = SeasonClass.objects.create(
                            season=season,
                            name=class_name,
                            team_level=team_level,
                            discipline=discipline,
                            sort_order=season.season_classes.count() * 10,
                            active=True,
                        )
                        stats["classes_created"] += 1
                else:
                    raise ValidationError(
                        f"Season class {row.get('season_class_name') or '—'} "
                        "could not be resolved during import."
                    )
                class_cache[class_key] = season_class

            if not membership.classes.filter(pk=season_class.pk).exists():
                if row.get("assign_class") or row.get("create_class"):
                    membership.classes.add(season_class)
                    stats["class_assignments_created"] += 1
                else:
                    raise ValidationError(
                        f"{rider}: {season_class.name} is no longer assigned to this rider."
                    )

            show_date = datetime.strptime(row["show_date"], "%Y-%m-%d").date()
            show = Show.objects.filter(
                team=season.team,
                season=season,
                name__iexact=row["show_name"],
                show_date=show_date,
                competition_level=row["competition_level"],
            ).first()
            if not show:
                show = Show.objects.create(
                    team=season.team,
                    season=season,
                    name=row["show_name"],
                    show_date=show_date,
                    competition_level=row["competition_level"],
                    is_historical_import=True,
                    status=Show.Status.COMPLETE,
                    venue=row.get("venue", ""),
                    futures_team_place=(
                        row.get("futures_team_place")
                        if row["competition_level"] != Show.CompetitionLevel.REGULAR
                        else None
                    ),
                    upper_team_place=(
                        row.get("upper_team_place")
                        if row["competition_level"] != Show.CompetitionLevel.REGULAR
                        else None
                    ),
                    notes="Imported historical results",
                )
            else:
                # A historical import may legitimately match an existing operational Show.
                # Never rewrite that shared operational show's status/metadata as a side effect
                # of importing rider history. Only historical-import-created Shows are enriched.
                if show.is_historical_import:
                    changed = []
                    if row.get("venue") and not show.venue:
                        show.venue = row["venue"]
                        changed.append("venue")
                    if show.status != Show.Status.COMPLETE:
                        show.status = Show.Status.COMPLETE
                        changed.append("status")
                    if row["competition_level"] != Show.CompetitionLevel.REGULAR:
                        for field in ("futures_team_place", "upper_team_place"):
                            incoming = row.get(field)
                            if incoming is not None and getattr(show, field) is None:
                                setattr(show, field, incoming)
                                changed.append(field)
                    if changed:
                        show.save(update_fields=changed)

            touched_shows.add(show.pk)
            show_class, _ = ShowClass.objects.get_or_create(
                show=show,
                season_class=season_class,
                defaults={
                    "name": season_class.name,
                    "discipline": season_class.discipline,
                    "sort_order": season_class.sort_order,
                },
            )
            track = row["competition_track"]
            entry_type = (
                ShowEntry.EntryType.TEAM
                if track == ShowEntry.CompetitionTrack.TEAM
                else ShowEntry.EntryType.INDIVIDUAL
            )
            entry, _ = ShowEntry.objects.get_or_create(
                show_class=show_class,
                rider=rider,
                competition_track=track,
                defaults={
                    "entry_type": entry_type,
                    "is_point_rider": False,
                    "status": ShowEntry.Status.ENTERED,
                    "notes": "Historical CSV import",
                },
            )
            if ShowResult.objects.filter(entry=entry).exists():
                stats["duplicates_skipped"] += 1
                continue

            entry.entry_type = entry_type
            entry.is_point_rider = False
            entry.status = ShowEntry.Status.ENTERED
            entry.save(update_fields=["entry_type", "is_point_rider", "status"])

            result = ShowResult(
                entry=entry,
                place=row.get("place"),
                horse_name=row.get("horse_name", ""),
                notes=row.get("notes", ""),
            )
            if row.get("points") != "":
                result.points = Decimal(row["points"])
                result.manual_points = True
            else:
                result.manual_points = False
            result.save()
            stats["results_created"] += 1

    stats["shows_touched"] = len(touched_shows)
    return stats

def _historical_import_bootstrap_counts(rows):
    rider_keys = set()
    membership_keys = set()
    class_keys = set()
    assignment_keys = set()
    iea_keys = set()

    for row in rows:
        rider_key = row.get("rider_id") or (
            f"{row.get('source_iea')}:{_history_import_norm(row.get('source_name'))}"
        )
        if row.get("create_rider"):
            rider_keys.add(rider_key)
        if row.get("create_membership"):
            membership_keys.add(rider_key)
        if row.get("create_class"):
            class_keys.add((
                row.get("team_level"),
                _history_import_norm(row.get("season_class_name")),
            ))
        if row.get("assign_class"):
            assignment_keys.add((
                rider_key,
                row.get("season_class_id") or _history_import_norm(row.get("season_class_name")),
            ))
        if row.get("set_iea_number"):
            iea_keys.add(rider_key)

    return {
        "riders": len(rider_keys),
        "memberships": len(membership_keys),
        "classes": len(class_keys),
        "assignments": len(assignment_keys),
        "iea_numbers": len(iea_keys),
    }

def _season_archive_readiness(season):
    incomplete_shows = list(
        season.shows.exclude(
            status__in=[Show.Status.COMPLETE, Show.Status.CANCELLED]
        ).order_by("show_date", "name")
    )
    resultless_entries = ShowEntry.objects.filter(
        show_class__show__season=season,
        status__in=[ShowEntry.Status.PLANNED, ShowEntry.Status.ENTERED],
        result__isnull=True,
    ).select_related(
        "rider", "show_class__show", "show_class__season_class"
    ).order_by(
        "show_class__show__show_date",
        "rider__last_name",
        "rider__first_name",
    )
    memberships_without_classes = list(
        season.memberships.select_related("rider")
        .annotate(class_count=Count("classes"))
        .filter(class_count=0)
        .order_by("rider__last_name", "rider__first_name")
    )
    open_family_charges = FamilyCharge.objects.filter(
        membership__season=season,
        status=FamilyCharge.Status.OPEN,
    ).select_related("membership__rider").order_by("due_date", "membership__rider__last_name")
    unresolved_reimbursements = ReimbursementRequest.objects.filter(
        season=season,
        status__in=[
            ReimbursementRequest.Status.DRAFT,
            ReimbursementRequest.Status.SUBMITTED,
            ReimbursementRequest.Status.APPROVED,
        ],
    ).order_by("-created_at")

    checks = [
        {
            "key": "incomplete_shows",
            "label": "Incomplete shows",
            "count": len(incomplete_shows),
            "severity": "warning",
            "detail": "Shows still in Planning, Registration open, or Entries submitted.",
        },
        {
            "key": "resultless_entries",
            "label": "Entries without results",
            "count": resultless_entries.count(),
            "severity": "warning",
            "detail": "Planned/entered rider entries that do not yet have a result.",
        },
        {
            "key": "memberships_without_classes",
            "label": "Riders without season classes",
            "count": len(memberships_without_classes),
            "severity": "warning",
            "detail": "Season roster records with no class assignments.",
        },
        {
            "key": "open_family_charges",
            "label": "Open family charges",
            "count": open_family_charges.count(),
            "severity": "finance",
            "detail": "Family receivables still marked Open for this season.",
        },
        {
            "key": "unresolved_reimbursements",
            "label": "Unresolved reimbursements",
            "count": unresolved_reimbursements.count(),
            "severity": "finance",
            "detail": "Draft, submitted, or approved reimbursement requests not yet resolved.",
        },
    ]

    issue_count = sum(check["count"] for check in checks)
    return {
        "checks": checks,
        "issue_count": issue_count,
        "ready": issue_count == 0,
        "incomplete_shows": incomplete_shows[:25],
        "resultless_entries": list(resultless_entries[:50]),
        "memberships_without_classes": memberships_without_classes[:25],
        "open_family_charges": list(open_family_charges[:25]),
        "unresolved_reimbursements": list(unresolved_reimbursements[:25]),
    }
