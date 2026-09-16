from datetime import date, time

from django.test import TestCase

from portal.model_modules.lessons import (
    LessonAttendanceRecord,
    LessonEnrollment,
    LessonOccurrence,
    LessonProgram,
    LessonSeries,
)
from portal.model_modules.people import OrganizationRoleAssignment, Person
from portal.models import Team
from portal.services.lesson_operations import materialize_lesson_series
from portal.services.lesson_scheduling import cancel_lesson_occurrence


class LessonSeriesMaterializationTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Operations Barn")
        self.instructor = Person.objects.create(team=self.team, first_name="Alex", last_name="Trainer")
        OrganizationRoleAssignment.objects.create(team=self.team, person=self.instructor, role=OrganizationRoleAssignment.Role.TRAINER)
        self.rider = Person.objects.create(team=self.team, first_name="Riley", last_name="Student")
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
        LessonEnrollment.objects.create(series=self.series, person=self.rider)

    def test_materialization_generates_and_prepares_series_window(self):
        result = materialize_lesson_series(self.series, date(2026, 9, 1), date(2026, 9, 15))
        self.assertEqual(len(result.generation.created), 3)
        self.assertEqual(len(result.prepared), 3)
        self.assertEqual(len(result.skipped), 0)
        for item in result.prepared:
            self.assertTrue(item.occurrence.attendance_records.filter(person=self.rider).exists())
            self.assertTrue(item.occurrence.assignments.filter(person=self.rider).exists())

    def test_materialization_is_end_to_end_idempotent(self):
        first = materialize_lesson_series(self.series, date(2026, 9, 1), date(2026, 9, 15))
        second = materialize_lesson_series(self.series, date(2026, 9, 1), date(2026, 9, 15))
        self.assertEqual(len(first.generation.created), 3)
        self.assertEqual(len(second.generation.created), 0)
        self.assertEqual(len(second.generation.existing), 3)
        self.assertEqual(LessonOccurrence.objects.count(), 3)
        self.assertEqual(LessonAttendanceRecord.objects.count(), 3)

    def test_materialization_preserves_existing_attendance(self):
        materialize_lesson_series(self.series, date(2026, 9, 1), date(2026, 9, 1))
        occurrence = LessonOccurrence.objects.get()
        attendance = occurrence.attendance_records.get(person=self.rider)
        attendance.status = LessonAttendanceRecord.Status.PRESENT
        attendance.save()
        materialize_lesson_series(self.series, date(2026, 9, 1), date(2026, 9, 1))
        attendance.refresh_from_db()
        self.assertEqual(attendance.status, LessonAttendanceRecord.Status.PRESENT)

    def test_materialization_skips_cancelled_existing_occurrence(self):
        first = materialize_lesson_series(self.series, date(2026, 9, 1), date(2026, 9, 1))
        occurrence = first.generation.created[0]
        cancel_lesson_occurrence(occurrence, notes="Weather")
        result = materialize_lesson_series(self.series, date(2026, 9, 1), date(2026, 9, 1))
        self.assertEqual(len(result.generation.created), 0)
        self.assertEqual(len(result.skipped), 1)
        occurrence.refresh_from_db()
        self.assertEqual(occurrence.status, LessonOccurrence.Status.CANCELLED)
        self.assertEqual(occurrence.notes, "Weather")

    def test_materialization_can_leave_existing_occurrences_unprepared(self):
        materialize_lesson_series(self.series, date(2026, 9, 1), date(2026, 9, 1))
        second_rider = Person.objects.create(team=self.team, first_name="Jordan", last_name="Student")
        LessonEnrollment.objects.create(series=self.series, person=second_rider)
        result = materialize_lesson_series(
            self.series,
            date(2026, 9, 1),
            date(2026, 9, 1),
            prepare_existing=False,
        )
        self.assertEqual(len(result.prepared), 0)
        occurrence = LessonOccurrence.objects.get()
        self.assertFalse(occurrence.attendance_records.filter(person=second_rider).exists())

    def test_new_enrollment_can_be_added_to_existing_scheduled_occurrence(self):
        materialize_lesson_series(self.series, date(2026, 9, 1), date(2026, 9, 1))
        second_rider = Person.objects.create(team=self.team, first_name="Jordan", last_name="Student")
        LessonEnrollment.objects.create(series=self.series, person=second_rider)
        result = materialize_lesson_series(self.series, date(2026, 9, 1), date(2026, 9, 1))
        self.assertEqual(len(result.prepared), 1)
        occurrence = LessonOccurrence.objects.get()
        self.assertTrue(occurrence.attendance_records.filter(person=second_rider).exists())
        self.assertTrue(occurrence.assignments.filter(person=second_rider).exists())
