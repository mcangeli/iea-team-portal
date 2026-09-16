from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from portal.model_modules.lessons import LessonAssignment, LessonAttendanceRecord, LessonOccurrence, LessonParticipantMove


@dataclass(frozen=True)
class LessonParticipantMoveResult:
    move: LessonParticipantMove
    source_attendance: LessonAttendanceRecord
    destination_attendance: LessonAttendanceRecord
    destination_assignment: LessonAssignment


DESTINATION_BLOCKING_ATTENDANCE_STATUSES = {
    LessonAttendanceRecord.Status.PRESENT,
    LessonAttendanceRecord.Status.ABSENT,
    LessonAttendanceRecord.Status.NO_SHOW,
    LessonAttendanceRecord.Status.MAKEUP,
}


def destination_has_capacity(destination_occurrence, person=None):
    capacity = destination_occurrence.capacity
    if capacity is None:
        return True
    roster = destination_occurrence.attendance_records.exclude(status=LessonAttendanceRecord.Status.CANCELLED)
    if person is not None:
        roster = roster.exclude(person=person)
    return roster.count() < capacity


def participant_has_active_move(source_occurrence, person):
    return LessonParticipantMove.objects.filter(source_occurrence=source_occurrence, person=person).exists()


def destination_accepts_participant(destination_occurrence, person):
    """A prepared EXPECTED slot may be reused; operational history may not."""
    attendance = LessonAttendanceRecord.objects.filter(
        occurrence=destination_occurrence,
        person=person,
    ).first()
    if not attendance:
        return True
    return attendance.status not in DESTINATION_BLOCKING_ATTENDANCE_STATUSES


def move_lesson_participant(*, source_occurrence, destination_occurrence, person, kind=LessonParticipantMove.Kind.MAKEUP, source_status=LessonAttendanceRecord.Status.EXCUSED, carry_horse=False, reason="", initiated_by=LessonParticipantMove.Initiator.STAFF, created_by=None):
    """Move one participant without rewriting lesson history."""
    if source_occurrence.status in {LessonOccurrence.Status.COMPLETED, LessonOccurrence.Status.CANCELLED}:
        raise ValidationError("Participants cannot be moved from a completed or cancelled lesson.")
    if destination_occurrence.status in {LessonOccurrence.Status.COMPLETED, LessonOccurrence.Status.CANCELLED}:
        raise ValidationError("Participants cannot be moved to a completed or cancelled lesson.")
    if destination_occurrence.starts_at <= source_occurrence.starts_at:
        raise ValidationError("The destination lesson must be after the original lesson.")
    if participant_has_active_move(source_occurrence, person):
        raise ValidationError("This rider has already been moved from the original lesson.")
    if not destination_accepts_participant(destination_occurrence, person):
        raise ValidationError("This rider already has attendance history for the destination lesson.")
    if not destination_has_capacity(destination_occurrence, person):
        raise ValidationError("The destination lesson is already at capacity.")

    try:
        with transaction.atomic():
            source_attendance = LessonAttendanceRecord.objects.select_for_update().filter(occurrence=source_occurrence, person=person).first()
            if not source_attendance:
                raise ValidationError("The rider is not on the source lesson roster.")
            source_assignment = LessonAssignment.objects.select_for_update().filter(occurrence=source_occurrence, person=person, role=LessonAssignment.Role.PARTICIPANT).first()
            if not source_assignment:
                raise ValidationError("The rider does not have a participant assignment on the source lesson.")

            if LessonParticipantMove.objects.filter(source_occurrence=source_occurrence, person=person).exists():
                raise ValidationError("This rider has already been moved from the original lesson.")

            destination_attendance = LessonAttendanceRecord.objects.select_for_update().filter(occurrence=destination_occurrence, person=person).first()
            if destination_attendance and destination_attendance.status in DESTINATION_BLOCKING_ATTENDANCE_STATUSES:
                raise ValidationError("This rider already has attendance history for the destination lesson.")
            if destination_attendance is None:
                destination_attendance = LessonAttendanceRecord.objects.create(
                    occurrence=destination_occurrence,
                    person=person,
                    status=LessonAttendanceRecord.Status.MAKEUP if kind == LessonParticipantMove.Kind.MAKEUP else LessonAttendanceRecord.Status.EXPECTED,
                )

            destination_assignment, _ = LessonAssignment.objects.get_or_create(
                occurrence=destination_occurrence,
                person=person,
                role=LessonAssignment.Role.PARTICIPANT,
            )

            move = LessonParticipantMove(
                source_occurrence=source_occurrence,
                destination_occurrence=destination_occurrence,
                person=person,
                kind=kind,
                source_status=source_status,
                carry_horse=carry_horse,
                reason=reason,
                initiated_by=initiated_by,
                initiated_by_user=created_by,
            )
            move.full_clean()

            source_attendance.status = source_status
            if reason:
                source_attendance.notes = reason
            source_attendance.full_clean()
            source_attendance.save(update_fields=["status", "notes", "recorded_at"])

            destination_attendance.status = LessonAttendanceRecord.Status.MAKEUP if kind == LessonParticipantMove.Kind.MAKEUP else LessonAttendanceRecord.Status.EXPECTED
            if reason:
                destination_attendance.notes = f"Moved from {source_occurrence.starts_at:%b %d}: {reason}"[:255]
            destination_attendance.full_clean()
            destination_attendance.save(update_fields=["status", "notes", "recorded_at"])

            if carry_horse and source_assignment.horse_id:
                destination_assignment.horse_id = source_assignment.horse_id
            destination_assignment.full_clean()
            destination_assignment.save()
            move.save()
    except IntegrityError as exc:
        raise ValidationError("This rider has already been moved from the original lesson.") from exc

    return LessonParticipantMoveResult(move, source_attendance, destination_attendance, destination_assignment)
