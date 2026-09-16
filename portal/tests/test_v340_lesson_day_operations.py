from datetime import date, time

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.horses import Horse
from portal.model_modules.lessons import LessonAssignment, LessonAttendanceRecord, LessonEnrollment, LessonOccurrence, LessonProgram, LessonSeries
from portal.model_modules.people import Person
from portal.models import Team
from portal.services.lesson_day_operations import LessonDayRowUpdate, update_lesson_day
from portal.services.lesson_preparation import prepare_lesson_occurrence
from portal.services.lesson_scheduling import generate_lesson_occurrences


class LessonDayOperationsTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Lesson Day Barn")
        self.admin = User.objects.create_superuser("lessonadmin", "lesson@example.com", "test")
        self.admin.profile.team = self.team; self.admin.profile.role = "admin"; self.admin.profile.save()
        self.rider1 = Person.objects.create(team=self.team, first_name="Avery", last_name="Rider")
        self.rider2 = Person.objects.create(team=self.team, first_name="Blake", last_name="Rider")
        self.program = LessonProgram.objects.create(team=self.team, name="Barn Lessons")
        self.series = LessonSeries.objects.create(program=self.program, name="Tuesday Group", weekday=1, starts_at_time=time(17), duration_minutes=60, start_date=date(2026,9,1), end_date=date(2026,10,31))
        LessonEnrollment.objects.create(series=self.series, person=self.rider1)
        LessonEnrollment.objects.create(series=self.series, person=self.rider2)
        self.occurrence = generate_lesson_occurrences(self.series, date(2026,9,22), date(2026,9,22)).created[0]
        prepare_lesson_occurrence(self.occurrence)
        self.scout = Horse.objects.create(team=self.team, name="Scout")
        self.client.force_login(self.admin)

    def _updates(self):
        return [
            LessonDayRowUpdate(self.rider1.pk, LessonAttendanceRecord.Status.PRESENT, self.scout.pk, "On time", "Flat"),
            LessonDayRowUpdate(self.rider2.pk, LessonAttendanceRecord.Status.ABSENT, None, "Sick", ""),
        ]

    def test_bulk_service_updates_attendance_and_horses_together(self):
        result = update_lesson_day(self.occurrence, self._updates())
        self.assertEqual(result.attendance_updated, 2); self.assertEqual(result.assignments_updated, 2); self.assertEqual(result.unassigned_horses, 1)
        attendance = LessonAttendanceRecord.objects.get(occurrence=self.occurrence, person=self.rider1)
        assignment = LessonAssignment.objects.get(occurrence=self.occurrence, person=self.rider1, role=LessonAssignment.Role.PARTICIPANT)
        self.assertEqual(attendance.status, LessonAttendanceRecord.Status.PRESENT); self.assertEqual(assignment.horse, self.scout)

    def test_bulk_service_rejects_foreign_horse_atomically(self):
        other = Team.objects.create(name="Other Barn"); foreign = Horse.objects.create(team=other, name="Foreign")
        updates = [LessonDayRowUpdate(self.rider1.pk, LessonAttendanceRecord.Status.PRESENT, foreign.pk), LessonDayRowUpdate(self.rider2.pk, LessonAttendanceRecord.Status.ABSENT)]
        with self.assertRaises(ValidationError): update_lesson_day(self.occurrence, updates)
        self.assertEqual(LessonAttendanceRecord.objects.get(occurrence=self.occurrence, person=self.rider1).status, LessonAttendanceRecord.Status.EXPECTED)

    def test_bulk_service_requires_complete_current_roster(self):
        with self.assertRaises(ValidationError): update_lesson_day(self.occurrence, [self._updates()[0]])

    def test_bulk_service_rejects_completed_lesson(self):
        self.occurrence.status = LessonOccurrence.Status.COMPLETED; self.occurrence.save()
        with self.assertRaises(ValidationError): update_lesson_day(self.occurrence, self._updates())

    def test_workspace_renders_every_participant_and_active_horse(self):
        response = self.client.get(reverse("lesson_day_workspace", args=[self.occurrence.pk]))
        self.assertContains(response, "Avery Rider"); self.assertContains(response, "Blake Rider"); self.assertContains(response, "Scout"); self.assertContains(response, "Save lesson day")

    def test_workspace_saves_whole_roster(self):
        response = self.client.post(reverse("lesson_day_workspace", args=[self.occurrence.pk]), {
            f"attendance_{self.rider1.pk}": LessonAttendanceRecord.Status.PRESENT,
            f"horse_{self.rider1.pk}": str(self.scout.pk),
            f"attendance_notes_{self.rider1.pk}": "Ready",
            f"assignment_notes_{self.rider1.pk}": "Poles",
            f"attendance_{self.rider2.pk}": LessonAttendanceRecord.Status.EXCUSED,
            f"horse_{self.rider2.pk}": "",
            f"attendance_notes_{self.rider2.pk}": "School event",
            f"assignment_notes_{self.rider2.pk}": "",
        }, follow=True)
        self.assertEqual(response.status_code, 200); self.assertContains(response, "1 participant(s) still need a horse assignment")
        self.assertEqual(LessonAttendanceRecord.objects.get(occurrence=self.occurrence, person=self.rider1).status, LessonAttendanceRecord.Status.PRESENT)
        self.assertEqual(LessonAssignment.objects.get(occurrence=self.occurrence, person=self.rider1, role=LessonAssignment.Role.PARTICIPANT).horse, self.scout)
