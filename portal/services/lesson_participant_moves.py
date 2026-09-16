from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction

from portal.model_modules.lessons import LessonAssignment, LessonAttendanceRecord, LessonOccurrence, LessonParticipantMove


@dataclass(frozen=True)
class LessonParticipantMoveResult:
    move: LessonParticipantMove
    source_attendance: LessonAttendanceRecord
    destination_attendance: LessonAttendanceRecord
    destination_assignment: LessonAssignment


def move_lesson_participant(*, source_occurrence, destination_occurrence, person, kind=LessonParticipantMove.Kind.MAKEUP, source_status=LessonAttendanceRecord.Status.EXCUSED, carry_horse=False, reason=""):
    """Move one participant without rewriting lesson history."""
    if source_occurrence.status in {LessonOccurrence.Status.COMPLETED, LessonOccurrence.Status.CANCELLED}:
        raise ValidationError("Participants cannot be moved from a completed or cancelled lesson.")

    with transaction.atomic():
        source_attendance = LessonAttendanceRecord.objects.select_for_update().filter(occurrence=source_occurrence, person=person).first()
        if not source_attendance:
            raise ValidationError("The rider is not on the source lesson roster.")
        source_assignment = LessonAssignment.objects.select_for_update().filter(occurrence=source_occurrence, person=person, role=LessonAssignment.Role.PARTICIPANT).first()
        if not source_assignment:
            raise ValidationError("The rider does not have a participant assignment on the source lesson.")

        move = LessonParticipantMove(source_occurrence=source_occurrence, destination_occurrence=destination_occurrence, person=person, kind=kind, source_status=source_status, carry_horse=carry_horse, reason=reason)
        move.full_clean()

        if LessonParticipantMove.objects.filter(source_occurrence=source_occurrence, destination_occurrence=destination_occurrence, person=person).exists():
            raise ValidationError("This rider has already been moved to that lesson.")

        destination_attendance, _ = LessonAttendanceRecord.objects.get_or_create(occurrence=destination_occurrence, person=person, defaults={"status": LessonAttendanceRecord.Status.MAKEUP if kind == LessonParticipantMove.Kind.MAKEUP else LessonAttendanceRecord.Status.EXPECTED})
        destination_assignment, _ = LessonAssignment.objects.get_or_create(occurrence=destination_occurrence, person=person, role=LessonAssignment.Role.PARTICIPANT)

        source_attendance.status = source_status
        if reason:
            source_attendance.notes = reason
        source_attendance.full_clean(); source_attendance.save(update_fields=["status", "notes", "recorded_at"])

        destination_attendance.status = LessonAttendanceRecord.Status.MAKEUP if kind == LessonParticipantMove.Kind.MAKEUP else LessonAttendanceRecord.Status.EXPECTED
        if reason:
            destination_attendance.notes = f"Moved from {source_occurrence.starts_at:%b %d}: {reason}"[:255]
        destination_attendance.full_clean(); destination_attendance.save(update_fields=["status", "notes", "recorded_at"])

        if carry_horse and source_assignment.horse_id:
            destination_assignment.horse_id = source_assignment.horse_id
        destination_assignment.full_clean(); destination_assignment.save()
        move.save()

    return LessonParticipantMoveResult(move, source_attendance, destination_attendance, destination_assignment)
