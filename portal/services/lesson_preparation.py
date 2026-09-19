from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from portal.model_modules.lessons import (
    LessonAssignment,
    LessonAttendanceRecord,
    LessonEnrollment,
    LessonOccurrence,
    IEALessonOccurrenceParticipant,
)
from portal.model_modules.people import LegacyPersonLink
from portal.models import SeasonMembership


@dataclass(frozen=True)
class LessonOccurrencePreparationResult:
    attendance_created: tuple[LessonAttendanceRecord, ...]
    attendance_existing: tuple[LessonAttendanceRecord, ...]
    assignments_created: tuple[LessonAssignment, ...]
    assignments_existing: tuple[LessonAssignment, ...]


def _occurrence_local_date(occurrence: LessonOccurrence):
    if timezone.is_aware(occurrence.starts_at):
        return timezone.localtime(occurrence.starts_at).date()
    return occurrence.starts_at.date()


def _enrollment_applies_to_occurrence(enrollment: LessonEnrollment, occurrence: LessonOccurrence) -> bool:
    if enrollment.status != LessonEnrollment.Status.ACTIVE:
        return False
    occurrence_date = _occurrence_local_date(occurrence)
    if enrollment.start_date and occurrence_date < enrollment.start_date:
        return False
    if enrollment.end_date and occurrence_date > enrollment.end_date:
        return False
    return True


def _barn_participants(occurrence: LessonOccurrence):
    enrollments = (
        occurrence.series.enrollments.select_related("person")
        .filter(status=LessonEnrollment.Status.ACTIVE)
        .order_by("person__last_name", "person__first_name", "id")
    )
    return [enrollment.person for enrollment in enrollments if _enrollment_applies_to_occurrence(enrollment, occurrence)]


def _iea_participants(occurrence: LessonOccurrence):
    context = occurrence.series.iea_context
    occurrence_date = _occurrence_local_date(occurrence)
    if occurrence_date < context.season.start_date or occurrence_date > context.season.end_date:
        raise ValidationError("IEA lesson occurrence must fall within its configured season.")

    explicit = list(
        IEALessonOccurrenceParticipant.objects.filter(occurrence=occurrence)
        .select_related("person")
        .order_by("person__last_name", "person__first_name", "id")
    )
    if explicit:
        return [row.person for row in explicit]

    # Compatibility fallback for pre-v3.6.2 IEA series/converted history. New
    # occurrence-first scheduling writes an explicit roster instead.
    memberships = SeasonMembership.objects.filter(season=context.season)
    if context.team_level != "mixed":
        memberships = memberships.filter(team_level=context.team_level)
    memberships = memberships.select_related("rider").order_by(
        "rider__last_name", "rider__first_name", "id"
    )
    rider_ids = [membership.rider_id for membership in memberships]
    links = {
        link.rider_id: link.person
        for link in LegacyPersonLink.objects.filter(rider_id__in=rider_ids).select_related("person")
    }
    missing = [membership.rider for membership in memberships if membership.rider_id not in links]
    if missing:
        names = ", ".join(str(rider) for rider in missing)
        raise ValidationError(f"IEA lesson roster contains rider(s) without canonical Person links: {names}.")
    return [links[membership.rider_id] for membership in memberships]


def _participants_for_occurrence(occurrence: LessonOccurrence):
    if occurrence.series.is_iea_series:
        return _iea_participants(occurrence)
    return _barn_participants(occurrence)


def prepare_lesson_occurrence(occurrence: LessonOccurrence) -> LessonOccurrencePreparationResult:
    """Materialize the operational lesson roster and instructor assignment.

    Barn series derive participants from LessonEnrollment. IEA occurrences prefer an
    explicit occurrence-level roster, allowing Futures and Upper riders to ride
    together. Pre-v3.6.2 IEA data falls back to season/team-level membership for
    compatibility. The occurrence instructor
    is materialized as an INSTRUCTOR assignment so the operational roster reflects
    both participants and staff. Preparation remains additive and idempotent;
    existing occurrence operations stay authoritative.
    """
    if not occurrence.pk:
        raise ValidationError("Lesson occurrence must be saved before preparation.")
    if occurrence.status not in {LessonOccurrence.Status.SCHEDULED, LessonOccurrence.Status.RESCHEDULED}:
        raise ValidationError("Only scheduled or rescheduled lesson occurrences can be prepared.")

    attendance_created = []
    attendance_existing = []
    assignments_created = []
    assignments_existing = []
    participants = _participants_for_occurrence(occurrence)

    with transaction.atomic():
        if occurrence.instructor_id:
            instructor_assignment, instructor_was_created = LessonAssignment.objects.get_or_create(
                occurrence=occurrence,
                person=occurrence.instructor,
                role=LessonAssignment.Role.INSTRUCTOR,
            )
            if instructor_was_created:
                instructor_assignment.full_clean()
                assignments_created.append(instructor_assignment)
            else:
                assignments_existing.append(instructor_assignment)

        for person in participants:
            attendance, attendance_was_created = LessonAttendanceRecord.objects.get_or_create(
                occurrence=occurrence,
                person=person,
                defaults={"status": LessonAttendanceRecord.Status.EXPECTED},
            )
            if attendance_was_created:
                attendance_created.append(attendance)
            else:
                attendance_existing.append(attendance)

            assignment, assignment_was_created = LessonAssignment.objects.get_or_create(
                occurrence=occurrence,
                person=person,
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
