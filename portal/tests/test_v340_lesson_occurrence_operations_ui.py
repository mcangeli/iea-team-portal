from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from portal.model_modules.horses import Horse
from portal.model_modules.lessons import LessonAssignment, LessonAttendanceRecord, LessonEnrollment, LessonOccurrence, LessonProgram, LessonSeries
from portal.model_modules.people import OrganizationRoleAssignment, Person
from portal.models import Team
from portal.services.lesson_scheduling import generate_lesson_occurrences


class LessonOccurrenceOperationsUITests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Operations Barn")
        self.admin = User.objects.create_superuser("admin", "admin@example.com", "test")
        # User creation auto-creates UserProfile. Scope that existing profile to
        # the organization exactly as the real portal authorization layer expects.
        self.admin.profile.team = self.team
        self.admin.profile.role = "admin"
        self.admin.profile.save()
        self.person = Person.objects.create(team=self.team, first_name="Riley", last_name="Rider")
        self.instructor = Person.objects.create(team=self.team, first_name="Casey", last_name="Coach")
        OrganizationRoleAssignment.objects.create(
            team=self.team,
            person=self.instructor,
            role=OrganizationRoleAssignment.Role.TRAINER,
        )
        self.program = LessonProgram.objects.create(team=self.team, name="Barn Program")
        self.series = LessonSeries.objects.create(program=self.program, name="Tuesday Lesson", instructor=self.instructor, weekday=1, starts_at_time=time(17), duration_minutes=60, start_date=date(2026,9,1), end_date=date(2026,10,31))
        LessonEnrollment.objects.create(series=self.series, person=self.person)
        self.occurrence = generate_lesson_occurrences(self.series, date(2026,9,22), date(2026,9,22)).created[0]
        self.client.force_login(self.admin)

    def test_workspace_shows_roster_source_and_origin(self):
        response = self.client.get(reverse("lesson_occurrence_detail", args=[self.occurrence.pk]))
        self.assertContains(response, "Barn lesson enrollment")
        self.assertContains(response, "Generated")
        self.assertContains(response, "Prepare / refresh roster")

    def test_prepare_materializes_attendance_and_assignment(self):
        response = self.client.post(reverse("lesson_occurrence_prepare", args=[self.occurrence.pk]), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(LessonAttendanceRecord.objects.filter(occurrence=self.occurrence, person=self.person).exists())
        self.assertTrue(LessonAssignment.objects.filter(occurrence=self.occurrence, person=self.person, role=LessonAssignment.Role.PARTICIPANT).exists())

    def test_attendance_can_be_updated(self):
        self.client.post(reverse("lesson_occurrence_prepare", args=[self.occurrence.pk]))
        record = LessonAttendanceRecord.objects.get(occurrence=self.occurrence, person=self.person)
        self.client.post(reverse("lesson_occurrence_attendance_edit", args=[record.pk]), {"status": LessonAttendanceRecord.Status.PRESENT, "notes": "Good ride"})
        record.refresh_from_db(); self.assertEqual(record.status, LessonAttendanceRecord.Status.PRESENT); self.assertEqual(record.notes, "Good ride")

    def test_horse_can_be_assigned(self):
        horse = Horse.objects.create(team=self.team, name="Scout")
        self.client.post(reverse("lesson_occurrence_prepare", args=[self.occurrence.pk]))
        assignment = LessonAssignment.objects.get(occurrence=self.occurrence, person=self.person, role=LessonAssignment.Role.PARTICIPANT)
        self.client.post(reverse("lesson_assignment_edit", args=[assignment.pk]), {"horse": horse.pk, "notes": "Flat lesson"})
        assignment.refresh_from_db(); self.assertEqual(assignment.horse, horse)

    def test_complete_locks_workspace_actions(self):
        self.client.post(reverse("lesson_occurrence_complete", args=[self.occurrence.pk]))
        self.occurrence.refresh_from_db(); self.assertEqual(self.occurrence.status, LessonOccurrence.Status.COMPLETED)
        response = self.client.get(reverse("lesson_occurrence_detail", args=[self.occurrence.pk]))
        self.assertNotContains(response, "Prepare / refresh roster")
        self.assertNotContains(response, "Reschedule")

    def test_cancel_marks_occurrence_cancelled(self):
        self.client.post(reverse("lesson_occurrence_cancel", args=[self.occurrence.pk]), {"notes": "Weather"})
        self.occurrence.refresh_from_db(); self.assertEqual(self.occurrence.status, LessonOccurrence.Status.CANCELLED); self.assertEqual(self.occurrence.notes, "Weather")

    def test_reschedule_preserves_original_slot(self):
        original_slot = self.occurrence.scheduled_for
        new_start = timezone.localtime(self.occurrence.starts_at + timedelta(days=1))
        new_end = new_start + timedelta(hours=1)
        self.client.post(reverse("lesson_occurrence_reschedule", args=[self.occurrence.pk]), {"starts_at": new_start.strftime("%Y-%m-%dT%H:%M"), "ends_at": new_end.strftime("%Y-%m-%dT%H:%M"), "notes": "Arena conflict"})
        self.occurrence.refresh_from_db(); self.assertEqual(self.occurrence.status, LessonOccurrence.Status.RESCHEDULED); self.assertEqual(self.occurrence.scheduled_for, original_slot)

    def test_assignment_form_restricts_horses_to_organization(self):
        other_team = Team.objects.create(name="Other Barn")
        other_horse = Horse.objects.create(team=other_team, name="Wrong Horse")
        self.client.post(reverse("lesson_occurrence_prepare", args=[self.occurrence.pk]))
        assignment = LessonAssignment.objects.get(occurrence=self.occurrence, person=self.person, role=LessonAssignment.Role.PARTICIPANT)
        response = self.client.post(reverse("lesson_assignment_edit", args=[assignment.pk]), {"horse": other_horse.pk, "notes": ""})
        self.assertEqual(response.status_code, 200)
        assignment.refresh_from_db(); self.assertIsNone(assignment.horse)


    def test_occurrence_attendance_route_does_not_collide_with_legacy_lesson_attendance(self):
        self.client.post(reverse("lesson_occurrence_prepare", args=[self.occurrence.pk]))
        record = LessonAttendanceRecord.objects.get(occurrence=self.occurrence, person=self.person)
        occurrence_url = reverse("lesson_occurrence_attendance_edit", args=[record.pk])
        legacy_url = reverse("lesson_attendance_edit", args=[record.pk])
        self.assertNotEqual(occurrence_url, legacy_url)
        self.assertEqual(occurrence_url, f"/lesson-attendance/{record.pk}/edit/")
