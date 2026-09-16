from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction

from portal.model_modules.lessons import (
    LessonAssignment,
    LessonAttendanceRecord,
    LessonEnrollment,
    LessonOccurrence,
)


@dataclass(frozen=True)
class LessonOccurrencePreparationResult:
    attendance_created: tuple[LessonAttendanceRecord, ...]
    attendance_existing: tuple[LessonAttendanceRecord, ...]
    assignments_created: tuple[LessonAssignment, ...]
    assignments_existing: tuple[LessonAssignment, ...]


def _enrollment_applies_to_occurrence(enrollment: LessonEnrollment, occurrence: LessonOccurrence) -> bool:
    if enrollment.status != LessonEnrollment.Status.ACTIVE:
        return False
    occurrence_date = occurrence.starts_at.date()
    if enrollment.start_date and occurrence_date < enrollment.start_date:
        return False
    if enrollment.end_date and occurrence_date > enrollment.end_date:
        return False
    return True


def prepare_lesson_occurrence(occurrence: LessonOccurrence) -> LessonOccurrencePreparationResult:
    """Materialize expected attendance and participant assignments from active enrollments.

    Preparation is additive and idempotent. Existing attendance and assignment rows
    are never rewritten, so operational changes made for an individual occurrence
    remain authoritative. Horse assignment is intentionally left blank for later
    occurrence-specific assignment.
    """
    if not occurrence.pk:
        raise ValidationError("Lesson occurrence must be saved before preparation.")
    if occurrence.status != LessonOccurrence.Status.SCHEDULED:
        raise ValidationError("Only scheduled lesson occurrences can be prepared from enrollment.")

    attendance_created = []
    attendance_existing = []
    assignments_created = []
    assignments_existing = []

    enrollments = (
        occurrence.series.enrollments.select_related("person")
        .filter(status=LessonEnrollment.Status.ACTIVE)
        .order_by("person__last_name", "person__first_name", "id")
    )

    with transaction.atomic():
        for enrollment in enrollments:
            if not _enrollment_applies_to_occurrence(enrollment, occurrence):
                continue

            attendance, attendance_was_created = LessonAttendanceRecord.objects.get_or_create(
                occurrence=occurrence,
                person=enrollment.person,
                defaults={"status": LessonAttendanceRecord.Status.EXPECTED},
            )
            if attendance_was_created:
                attendance_created.append(attendance)
            else:
                attendance_existing.append(attendance)

            assignment, assignment_was_created = LessonAssignment.objects.get_or_create(
                occurrence=occurrence,
                person=enrollment.person,
                role=LessonAssignment.Role.PARTICIPANT,
            )
            if assignment_was_created:
                assignments_created.append(assignment)
            else:
                assignments_existing.append(assignment)

    return LessonOccurrencePreparationResult(
        tuple(attendance_created),
        tuple(attendance_existing),
        tuple(assignments_created),
        tuple(assignments_existing),
    )
