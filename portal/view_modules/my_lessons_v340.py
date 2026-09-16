from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from ..model_modules.lessons import LessonAttendanceRecord, LessonOccurrence, LessonParticipantMove
from ..services.lesson_participant_moves import destination_accepts_participant, destination_has_capacity, move_lesson_participant, participant_has_active_move


def _rider_person(user):
    person = getattr(user, "arena_person", None)
    if not person or not person.active:
        raise PermissionDenied("A linked active rider profile is required.")
    if not person.role_assignments.filter(role="rider", active=True).exists():
        raise PermissionDenied("Rider access is required.")
    return person


def _destinations(source, person):
    if participant_has_active_move(source, person):
        return []
    qs = LessonOccurrence.objects.filter(
        series__program__team=person.team,
        starts_at__gt=max(source.starts_at, timezone.now()),
    ).exclude(pk=source.pk).exclude(
        status__in=[LessonOccurrence.Status.COMPLETED, LessonOccurrence.Status.CANCELLED]
    ).select_related("series__program", "series__iea_context__season").distinct().order_by("starts_at")
    if source.series.is_iea_series:
        context = source.series.iea_context
        qs = qs.filter(series__iea_context__season=context.season, series__iea_context__team_level=context.team_level)
    else:
        qs = qs.filter(series__iea_context__isnull=True, series__program=source.series.program)
    return [
        row for row in qs[:40]
        if destination_accepts_participant(row, person) and destination_has_capacity(row, person)
    ][:20]


@login_required
def my_lessons(request):
    person = _rider_person(request.user)
    upcoming = list(LessonAttendanceRecord.objects.filter(
        person=person,
        occurrence__starts_at__gte=timezone.now(),
    ).exclude(occurrence__status=LessonOccurrence.Status.CANCELLED).select_related(
        "occurrence__series__program", "occurrence__series__iea_context__season"
    ).order_by("occurrence__starts_at"))
    occurrence_ids = [row.occurrence_id for row in upcoming]
    moves = LessonParticipantMove.objects.filter(person=person).filter(
        source_occurrence_id__in=occurrence_ids
    ) | LessonParticipantMove.objects.filter(person=person, destination_occurrence_id__in=occurrence_ids)
    source_moves = {move.source_occurrence_id: move for move in moves.select_related("source_occurrence", "destination_occurrence", "created_by")}
    destination_moves = {move.destination_occurrence_id: move for move in moves.select_related("source_occurrence", "destination_occurrence", "created_by")}
    schedule = [{
        "attendance": attendance,
        "moved_to": source_moves.get(attendance.occurrence_id),
        "makeup_from": destination_moves.get(attendance.occurrence_id),
    } for attendance in upcoming]
    return render(request, "portal/my_lessons.html", {"person": person, "upcoming": upcoming, "schedule": schedule})


@login_required
def my_lesson_reschedule(request, pk):
    person = _rider_person(request.user)
    source = get_object_or_404(
        LessonOccurrence.objects.select_related("series__program", "series__iea_context__season"),
        pk=pk,
        series__program__team=person.team,
        attendance_records__person=person,
    )
    if source.status in {LessonOccurrence.Status.COMPLETED, LessonOccurrence.Status.CANCELLED} or source.starts_at <= timezone.now():
        raise PermissionDenied("This lesson can no longer be rescheduled.")
    if participant_has_active_move(source, person):
        raise PermissionDenied("This lesson has already been rescheduled.")
    destinations = _destinations(source, person)
    if request.method == "POST":
        try:
            destination_id = int(request.POST.get("destination_occurrence", ""))
            destination = next((row for row in destinations if row.pk == destination_id), None)
            if destination is None:
                raise ValidationError("Select an available eligible lesson.")
            result = move_lesson_participant(
                source_occurrence=source,
                destination_occurrence=destination,
                person=person,
                kind=LessonParticipantMove.Kind.MAKEUP,
                source_status=LessonAttendanceRecord.Status.EXCUSED,
                carry_horse=False,
                reason=request.POST.get("reason", "").strip(),
                initiated_by=LessonParticipantMove.Initiator.RIDER,
                created_by=request.user,
            )
            messages.success(request, f"Your lesson has been rescheduled for {result.move.destination_occurrence.starts_at:%b %d at %I:%M %p}.")
            return redirect("my_lessons")
        except (ValidationError, ValueError) as exc:
            messages.error(request, "; ".join(exc.messages) if isinstance(exc, ValidationError) else "Select a lesson.")
    return render(request, "portal/my_lesson_reschedule.html", {"person": person, "occurrence": source, "destinations": destinations})
