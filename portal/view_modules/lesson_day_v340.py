from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from ..model_modules.horses import Horse
from ..model_modules.lessons import LessonAssignment, LessonAttendanceRecord, LessonOccurrence, LessonParticipantMove
from ..platform import organization_for_view_user
from ..services.lesson_day_operations import LessonDayRowUpdate, update_lesson_day
from ..services.lesson_participant_moves import move_lesson_participant
from .common import _require_manage


def _occurrence_for_team(team, pk):
    return get_object_or_404(
        LessonOccurrence.objects.select_related("series__program", "series__iea_context__season", "instructor"),
        pk=pk,
        series__program__team=team,
    )


def _move_destinations(occurrence, person):
    qs = LessonOccurrence.objects.filter(
        series__program__team=occurrence.series.program.team,
        starts_at__gt=occurrence.starts_at,
    ).exclude(pk=occurrence.pk).exclude(
        status__in=[LessonOccurrence.Status.COMPLETED, LessonOccurrence.Status.CANCELLED]
    ).select_related("series__program", "series__iea_context__season")

    if occurrence.series.is_iea_series:
        context = occurrence.series.iea_context
        qs = qs.filter(
            series__iea_context__season=context.season,
            series__iea_context__team_level=context.team_level,
        )
    else:
        qs = qs.filter(series__iea_context__isnull=True)

    qs = qs.exclude(attendance_records__person=person).distinct().order_by("starts_at")
    return qs[:20]


@login_required
def lesson_day_workspace(request, pk):
    _require_manage(request.user)
    team = organization_for_view_user(request.user)
    occurrence = _occurrence_for_team(team, pk)
    editable = occurrence.status not in {LessonOccurrence.Status.COMPLETED, LessonOccurrence.Status.CANCELLED}

    attendance = list(occurrence.attendance_records.select_related("person").order_by("person__last_name", "person__first_name", "person_id"))
    assignments = {
        row.person_id: row
        for row in occurrence.assignments.filter(role=LessonAssignment.Role.PARTICIPANT).select_related("person", "horse")
    }
    rows = [{"attendance": record, "assignment": assignments.get(record.person_id)} for record in attendance]
    horses = Horse.objects.filter(team=team, active=True).order_by("name")

    if request.method == "POST":
        if not editable:
            messages.error(request, "Completed or cancelled lessons cannot be edited.")
            return redirect("lesson_day_workspace", pk=pk)
        try:
            updates = []
            for row in rows:
                person_id = row["attendance"].person_id
                horse_value = request.POST.get(f"horse_{person_id}", "").strip()
                updates.append(LessonDayRowUpdate(
                    person_id=person_id,
                    attendance_status=request.POST.get(f"attendance_{person_id}", ""),
                    horse_id=int(horse_value) if horse_value else None,
                    attendance_notes=request.POST.get(f"attendance_notes_{person_id}", "").strip(),
                    assignment_notes=request.POST.get(f"assignment_notes_{person_id}", "").strip(),
                ))
            result = update_lesson_day(occurrence, updates)
            if result.unassigned_horses:
                messages.warning(request, f"Lesson day saved. {result.unassigned_horses} participant(s) still need a horse assignment.")
            else:
                messages.success(request, "Lesson day saved. Attendance and horse assignments are complete.")
            return redirect("lesson_day_workspace", pk=pk)
        except (ValidationError, ValueError) as exc:
            messages.error(request, "; ".join(exc.messages) if isinstance(exc, ValidationError) else "Invalid horse selection.")

    return render(request, "portal/lesson_day_workspace.html", {
        "occurrence": occurrence,
        "rows": rows,
        "horses": horses,
        "attendance_choices": LessonAttendanceRecord.Status.choices,
        "editable": editable,
        "unassigned_count": sum(1 for row in rows if row["assignment"] and not row["assignment"].horse_id),
    })


@login_required
def lesson_participant_move(request, pk, person_pk):
    _require_manage(request.user)
    team = organization_for_view_user(request.user)
    occurrence = _occurrence_for_team(team, pk)
    attendance = get_object_or_404(
        occurrence.attendance_records.select_related("person"), person_id=person_pk
    )
    person = attendance.person
    destinations = _move_destinations(occurrence, person)

    if request.method == "POST":
        try:
            destination_id = int(request.POST.get("destination_occurrence", ""))
            destination = _occurrence_for_team(team, destination_id)
            allowed_ids = {row.pk for row in _move_destinations(occurrence, person)}
            if destination.pk not in allowed_ids:
                raise ValidationError("Select an eligible upcoming lesson for this rider.")
            kind = request.POST.get("kind", LessonParticipantMove.Kind.MAKEUP)
            if kind not in {LessonParticipantMove.Kind.MOVE, LessonParticipantMove.Kind.MAKEUP}:
                raise ValidationError("Select a valid move type.")
            source_status = request.POST.get("source_status", LessonAttendanceRecord.Status.EXCUSED)
            if source_status not in {value for value, _label in LessonAttendanceRecord.Status.choices}:
                raise ValidationError("Select a valid status for the original lesson.")
            move_lesson_participant(
                source_occurrence=occurrence,
                destination_occurrence=destination,
                person=person,
                kind=kind,
                source_status=source_status,
                carry_horse=request.POST.get("carry_horse") == "on",
                reason=request.POST.get("reason", "").strip(),
            )
            label = "make-up" if kind == LessonParticipantMove.Kind.MAKEUP else "move"
            messages.success(request, f"{person} {label} scheduled for {destination.starts_at:%b %d at %I:%M %p}.")
            return redirect("lesson_day_workspace", pk=occurrence.pk)
        except (ValidationError, ValueError) as exc:
            messages.error(request, "; ".join(exc.messages) if isinstance(exc, ValidationError) else "Select a destination lesson.")

    return render(request, "portal/lesson_participant_move.html", {
        "occurrence": occurrence,
        "attendance": attendance,
        "person": person,
        "destinations": destinations,
        "kind_choices": LessonParticipantMove.Kind.choices,
        "source_status_choices": LessonAttendanceRecord.Status.choices,
    })
