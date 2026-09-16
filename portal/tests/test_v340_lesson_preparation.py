from datetime import date, datetime, time, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from portal.model_modules.horses import Horse
from portal.model_modules.lessons import (
    LessonAssignment,
    LessonAttendanceRecord,
    LessonEnrollment,
    LessonOccurrence,
    LessonProgram,
    LessonSeries,
)
from portal.model_modules.people import Person
from portal.models import Team
from portal.services.lesson_preparation import prepare_lesson_occurrence


class LessonOccurrencePreparationTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Preparation Barn")
        self.instructor = Person.objects.create(team=self.team, first_name="Alex", last_name="Trainer")
        self.rider = Person.objects.create(team=self.team, first_name="Riley", last_name="Student")
        self.second_rider = Person.objects.create(team=self.team, first_name="Jordan", last_name="Student")
        self.program = LessonProgram.objects.create(team=self.team, name="Lesson Program", default_capacity=6)
        self.series = LessonSeries.objects.create(
            program=self.program,
            name="Tuesday Intermediate",
            instructor=self.instructor,
            weekday=1,
            starts_at_time=time(17, 0),
            duration_minutes=60,
            start_date=date(2026, 9, 1),
            end_date=date(2026, 10, 31),
        )
        starts_at = timezone.make_aware(datetime(2026, 9, 22, 17, 0))
        self.occurrence = LessonOccurrence.objects.create(
            series=self.series,
            title=self.series.name,
            instructor=self.instructor,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(minutes=60),
            capacity=6,
        )

    def test_active_enrollment_materializes_expected_attendance_and_participant_assignment(self):
        LessonEnrollment.objects.create(series=self.series, person=self.rider)
        result = prepare_lesson_occurrence(self.occurrence)
        self.assertEqual(len(result.attendance_created), 1)
        self.assertEqual(len(result.assignments_created), 1)
        attendance = LessonAttendanceRecord.objects.get(occurrence=self.occurrence, person=self.rider)
        assignment = LessonAssignment.objects.get(occurrence=self.occurrence, person=self.rider)
        self.assertEqual(attendance.status, LessonAttendanceRecord.Status.EXPECTED)
        self.assertEqual(assignment.role, LessonAssignment.Role.PARTICIPANT)
        self.assertIsNone(assignment.horse)

    def test_preparation_is_idempotent(self):
        LessonEnrollment.objects.create(series=self.series, person=self.rider)
        first = prepare_lesson_occurrence(self.occurrence)
        second = prepare_lesson_occurrence(self.occurrence)
        self.assertEqual(len(first.attendance_created), 1)
        self.assertEqual(len(first.assignments_created), 1)
        self.assertEqual(len(second.attendance_created), 0)
        self.assertEqual(len(second.assignments_created), 0)
        self.assertEqual(len(second.attendance_existing), 1)
        self.assertEqual(len(second.assignments_existing), 1)

    def test_waitlisted_withdrawn_and_completed_enrollments_are_not_materialized(self):
        for index, status in enumerate((
            LessonEnrollment.Status.WAITLISTED,
            LessonEnrollment.Status.WITHDRAWN,
            LessonEnrollment.Status.COMPLETED,
        )):
            person = Person.objects.create(team=self.team, first_name=f"Rider{index}", last_name="Inactive")
            LessonEnrollment.objects.create(series=self.series, person=person, status=status)
        prepare_lesson_occurrence(self.occurrence)
        self.assertEqual(self.occurrence.attendance_records.count(), 0)
        self.assertEqual(self.occurrence.assignments.count(), 0)

    def test_enrollment_date_window_controls_occurrence_membership(self):
        LessonEnrollment.objects.create(
            series=self.series,
            person=self.rider,
            start_date=date(2026, 9, 23),
        )
        LessonEnrollment.objects.create(
            series=self.series,
            person=self.second_rider,
            end_date=date(2026, 9, 21),
        )
        prepare_lesson_occurrence(self.occurrence)
        self.assertEqual(self.occurrence.attendance_records.count(), 0)
        self.assertEqual(self.occurrence.assignments.count(), 0)

    def test_enrollment_boundaries_are_inclusive(self):
        LessonEnrollment.objects.create(
            series=self.series,
            person=self.rider,
            start_date=date(2026, 9, 22),
            end_date=date(2026, 9, 22),
        )
        prepare_lesson_occurrence(self.occurrence)
        self.assertTrue(self.occurrence.attendance_records.filter(person=self.rider).exists())

    def test_preparation_preserves_existing_attendance_status(self):
        LessonEnrollment.objects.create(series=self.series, person=self.rider)
        LessonAttendanceRecord.objects.create(
            occurrence=self.occurrence,
            person=self.rider,
            status=LessonAttendanceRecord.Status.PRESENT,
        )
        result = prepare_lesson_occurrence(self.occurrence)
        attendance = LessonAttendanceRecord.objects.get(occurrence=self.occurrence, person=self.rider)
        self.assertEqual(attendance.status, LessonAttendanceRecord.Status.PRESENT)
        self.assertEqual(len(result.attendance_created), 0)
        self.assertEqual(len(result.attendance_existing), 1)

    def test_preparation_preserves_existing_horse_assignment(self):
        LessonEnrollment.objects.create(series=self.series, person=self.rider)
        horse = Horse.objects.create(team=self.team, name="Comet")
        LessonAssignment.objects.create(
            occurrence=self.occurrence,
            person=self.rider,
            role=LessonAssignment.Role.PARTICIPANT,
            horse=horse,
        )
        result = prepare_lesson_occurrence(self.occurrence)
        assignment = LessonAssignment.objects.get(occurrence=self.occurrence, person=self.rider)
        self.assertEqual(assignment.horse, horse)
        self.assertEqual(len(result.assignments_created), 0)
        self.assertEqual(len(result.assignments_existing), 1)

    def test_preparation_does_not_remove_person_after_enrollment_changes(self):
        enrollment = LessonEnrollment.objects.create(series=self.series, person=self.rider)
        prepare_lesson_occurrence(self.occurrence)
        enrollment.status = LessonEnrollment.Status.WITHDRAWN
        enrollment.save()
        prepare_lesson_occurrence(self.occurrence)
        self.assertTrue(self.occurrence.attendance_records.filter(person=self.rider).exists())
        self.assertTrue(self.occurrence.assignments.filter(person=self.rider).exists())

    def test_preparation_rejects_cancelled_completed_and_rescheduled_occurrences(self):
        LessonEnrollment.objects.create(series=self.series, person=self.rider)
        for status in (
            LessonOccurrence.Status.CANCELLED,
            LessonOccurrence.Status.COMPLETED,
            LessonOccurrence.Status.RESCHEDULED,
        ):
            self.occurrence.status = status
            self.occurrence.save()
            with self.assertRaises(ValidationError):
                prepare_lesson_occurrence(self.occurrence)
        self.assertEqual(self.occurrence.attendance_records.count(), 0)

    def test_multiple_active_enrollments_prepare_independently(self):
        LessonEnrollment.objects.create(series=self.series, person=self.rider)
        LessonEnrollment.objects.create(series=self.series, person=self.second_rider)
        result = prepare_lesson_occurrence(self.occurrence)
        self.assertEqual(len(result.attendance_created), 2)
        self.assertEqual(len(result.assignments_created), 2)
        self.assertEqual(self.occurrence.attendance_records.count(), 2)
        self.assertEqual(self.occurrence.assignments.filter(role=LessonAssignment.Role.PARTICIPANT).count(), 2)
