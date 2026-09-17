from django.core.exceptions import ValidationError
from django.db import transaction

from portal.model_modules.lessons import LessonAttendanceRecord, LessonOccurrence


@transaction.atomic
def complete_lesson_occurrence(occurrence: LessonOccurrence) -> LessonOccurrence:
    """Close a lesson only after its attendance has been operationally resolved."""
    occurrence = (
        LessonOccurrence.objects.select_for_update()
        .select_related("series__program")
        .get(pk=occurrence.pk)
    )

    if occurrence.status == LessonOccurrence.Status.CANCELLED:
        raise ValidationError("A cancelled lesson cannot be completed.")
    if occurrence.status == LessonOccurrence.Status.COMPLETED:
        return occurrence

    unresolved = occurrence.attendance_records.filter(
        status=LessonAttendanceRecord.Status.EXPECTED
    )
    if unresolved.exists():
        raise ValidationError(
            "Attendance must be resolved for every participant before completing the lesson."
        )

    occurrence.status = LessonOccurrence.Status.COMPLETED
    occurrence.full_clean()
    occurrence.save(update_fields=["status", "updated_at"])
    return occurrence
