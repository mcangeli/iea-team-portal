from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction

from portal.model_modules.horses import Horse
from portal.model_modules.lessons import LessonAssignment, LessonAttendanceRecord, LessonOccurrence


@dataclass(frozen=True)
class LessonDayRowUpdate:
    person_id: int
    attendance_status: str
    horse_id: int | None = None
    attendance_notes: str = ""
    assignment_notes: str = ""


@dataclass(frozen=True)
class LessonDayUpdateResult:
    attendance_updated: int
    assignments_updated: int
    unassigned_horses: int


def update_lesson_day(occurrence: LessonOccurrence, rows: list[LessonDayRowUpdate]) -> LessonDayUpdateResult:
    """Atomically update attendance and participant horse assignments for one lesson."""
    if occurrence.status in {LessonOccurrence.Status.COMPLETED, LessonOccurrence.Status.CANCELLED}:
        raise ValidationError("Completed or cancelled lessons cannot be edited.")

    valid_statuses = {value for value, _label in LessonAttendanceRecord.Status.choices}
    team_id = occurrence.series.program.team_id
    requested_ids = {row.person_id for row in rows}
    if len(requested_ids) != len(rows):
        raise ValidationError("Each lesson participant may only appear once.")

    with transaction.atomic():
        attendance = {row.person_id: row for row in occurrence.attendance_records.select_for_update().select_related("person")}
        assignments = {
            row.person_id: row
            for row in occurrence.assignments.select_for_update().filter(role=LessonAssignment.Role.PARTICIPANT).select_related("person", "horse")
        }
        if requested_ids != set(attendance) or requested_ids != set(assignments):
            raise ValidationError("Lesson-day roster changed. Refresh the page before saving.")

        horse_ids = {row.horse_id for row in rows if row.horse_id}
        horses = {horse.pk: horse for horse in Horse.objects.filter(team_id=team_id, active=True, pk__in=horse_ids)}
        if set(horses) != horse_ids:
            raise ValidationError("One or more selected horses are not active for this organization.")

        attendance_updated = 0
        assignments_updated = 0
        unassigned = 0
        for update in rows:
            if update.attendance_status not in valid_statuses:
                raise ValidationError("Invalid attendance status.")
            record = attendance[update.person_id]
            assignment = assignments[update.person_id]
            record.status = update.attendance_status
            record.notes = update.attendance_notes
            record.full_clean(); record.save(update_fields=["status", "notes", "recorded_at"])
            attendance_updated += 1
            assignment.horse = horses.get(update.horse_id)
            assignment.notes = update.assignment_notes
            assignment.full_clean(); assignment.save(update_fields=["horse", "notes", "updated_at"])
            assignments_updated += 1
            if assignment.horse_id is None:
                unassigned += 1

    return LessonDayUpdateResult(attendance_updated, assignments_updated, unassigned)
