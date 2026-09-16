from datetime import date, time

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.lessons import LessonAttendanceRecord, LessonEnrollment, LessonOccurrence, LessonProgram, LessonSeries
from portal.model_modules.people import Person
from portal.models import Team
from portal.services.lesson_completion import complete_lesson_occurrence
from portal.services.lesson_day_operations import LessonDayRowUpdate, update_lesson_day
from portal.services.lesson_preparation import prepare_lesson_occurrence
from portal.services.lesson_scheduling import generate_lesson_occurrences


class LessonCompletionTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Completion Barn")
        self.admin = User.objects.create_superuser("completionadmin", "completion@example.com", "test")
        self.admin.profile.team = self.team
        self.admin.profile.role = "admin"
        self.admin.profile.save()
        self.rider = Person.objects.create(team=self.team, first_name="Avery", last_name="Rider")
        self.program = LessonProgram.objects.create(team=self.team, name="Barn Lessons")
        self.series = LessonSeries.objects.create(
            program=self.program,
            name="Tuesday Group",
            weekday=1,
            starts_at_time=time(17),
            duration_minutes=60,
            start_date=date(2026, 9, 1),
            end_date=date(2026, 10, 31),
        )
        LessonEnrollment.objects.create(series=self.series, person=self.rider)
        self.occurrence = generate_lesson_occurrences(
            self.series, date(2026, 9, 22), date(2026, 9, 22)
        ).created[0]
        prepare_lesson_occurrence(self.occurrence)
        self.client.force_login(self.admin)

    def test_service_rejects_unresolved_expected_attendance(self):
        with self.assertRaisesMessage(ValidationError, "Attendance must be resolved"):
            complete_lesson_occurrence(self.occurrence)
        self.occurrence.refresh_from_db()
        self.assertEqual(self.occurrence.status, LessonOccurrence.Status.SCHEDULED)

    def test_service_completes_after_attendance_is_resolved(self):
        record = LessonAttendanceRecord.objects.get(occurrence=self.occurrence, person=self.rider)
        record.status = LessonAttendanceRecord.Status.PRESENT
        record.save()
        completed = complete_lesson_occurrence(self.occurrence)
        self.assertEqual(completed.status, LessonOccurrence.Status.COMPLETED)

    def test_service_rejects_cancelled_lesson(self):
        self.occurrence.status = LessonOccurrence.Status.CANCELLED
        self.occurrence.save()
        with self.assertRaisesMessage(ValidationError, "cancelled lesson"):
            complete_lesson_occurrence(self.occurrence)

    def test_service_completion_is_idempotent(self):
        record = LessonAttendanceRecord.objects.get(occurrence=self.occurrence, person=self.rider)
        record.status = LessonAttendanceRecord.Status.ABSENT
        record.save()
        complete_lesson_occurrence(self.occurrence)
        completed = complete_lesson_occurrence(self.occurrence)
        self.assertEqual(completed.status, LessonOccurrence.Status.COMPLETED)

    def test_completion_view_reports_unresolved_attendance(self):
        response = self.client.post(
            reverse("lesson_occurrence_complete", args=[self.occurrence.pk]),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Attendance must be resolved")
        self.occurrence.refresh_from_db()
        self.assertEqual(self.occurrence.status, LessonOccurrence.Status.SCHEDULED)

    def test_completion_view_closes_resolved_lesson(self):
        record = LessonAttendanceRecord.objects.get(occurrence=self.occurrence, person=self.rider)
        record.status = LessonAttendanceRecord.Status.EXCUSED
        record.save()
        response = self.client.post(
            reverse("lesson_occurrence_complete", args=[self.occurrence.pk]),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lesson marked complete")
        self.occurrence.refresh_from_db()
        self.assertEqual(self.occurrence.status, LessonOccurrence.Status.COMPLETED)

    def test_completed_lesson_remains_immutable_in_lesson_day_service(self):
        record = LessonAttendanceRecord.objects.get(occurrence=self.occurrence, person=self.rider)
        record.status = LessonAttendanceRecord.Status.PRESENT
        record.save()
        complete_lesson_occurrence(self.occurrence)
        with self.assertRaisesMessage(ValidationError, "cannot be edited"):
            update_lesson_day(
                self.occurrence,
                [LessonDayRowUpdate(self.rider.pk, LessonAttendanceRecord.Status.ABSENT)],
            )
