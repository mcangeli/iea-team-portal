from datetime import date, time

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.lessons import LessonEnrollment, LessonOccurrence, LessonProgram, LessonSeries
from portal.model_modules.people import Person
from portal.models import Team


class LessonSeriesUITests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Series UI Barn")
        self.admin = User.objects.create_user(username="seriesadmin", password="test-pass")
        self.admin.profile.team = self.team
        self.admin.profile.role = "admin"
        self.admin.profile.save()
        self.client.login(username="seriesadmin", password="test-pass")
        self.rider = Person.objects.create(team=self.team, first_name="Riley", last_name="Student")
        self.program = LessonProgram.objects.create(team=self.team, name="Academy", default_capacity=6)
        self.series = LessonSeries.objects.create(
            program=self.program,
            name="Tuesday Intermediate",
            weekday=1,
            starts_at_time=time(17, 0),
            duration_minutes=60,
            start_date=date(2026, 9, 1),
            end_date=date(2026, 10, 31),
            active=True,
        )

    def test_series_detail_renders_roster_and_schedule(self):
        LessonEnrollment.objects.create(series=self.series, person=self.rider)
        response = self.client.get(reverse("lesson_series_detail", args=[self.series.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tuesday Intermediate")
        self.assertContains(response, "Riley Student")
        self.assertContains(response, "Generate schedule")

    def test_admin_can_add_enrollment(self):
        response = self.client.post(reverse("lesson_enrollment_create", args=[self.series.pk]), {
            "person": self.rider.pk,
            "status": LessonEnrollment.Status.ACTIVE,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(LessonEnrollment.objects.filter(series=self.series, person=self.rider).exists())

    def test_enrollment_person_is_organization_scoped(self):
        other_team = Team.objects.create(name="Other Barn")
        other_person = Person.objects.create(team=other_team, first_name="Other", last_name="Rider")
        response = self.client.post(reverse("lesson_enrollment_create", args=[self.series.pk]), {
            "person": other_person.pk,
            "status": LessonEnrollment.Status.ACTIVE,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(LessonEnrollment.objects.filter(series=self.series, person=other_person).exists())

    def test_generate_schedule_materializes_occurrences_and_roster(self):
        LessonEnrollment.objects.create(series=self.series, person=self.rider)
        response = self.client.post(reverse("lesson_series_generate", args=[self.series.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertGreater(self.series.occurrences.count(), 0)
        occurrence = self.series.occurrences.first()
        self.assertTrue(occurrence.attendance_records.filter(person=self.rider).exists())
        self.assertTrue(occurrence.assignments.filter(person=self.rider).exists())

    def test_occurrence_detail_renders_attendance_and_assignment(self):
        LessonEnrollment.objects.create(series=self.series, person=self.rider)
        self.client.post(reverse("lesson_series_generate", args=[self.series.pk]))
        occurrence = self.series.occurrences.first()
        response = self.client.get(reverse("lesson_occurrence_detail", args=[occurrence.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Riley Student")
        self.assertContains(response, "Horse not assigned")

    def test_series_and_occurrence_are_organization_scoped(self):
        other_team = Team.objects.create(name="Other Barn")
        other_program = LessonProgram.objects.create(team=other_team, name="Private")
        other_series = LessonSeries.objects.create(program=other_program, name="Private Series")
        self.assertEqual(self.client.get(reverse("lesson_series_detail", args=[other_series.pk])).status_code, 404)
        occurrence = LessonOccurrence.objects.create(
            series=other_series,
            title="Private Lesson",
            starts_at="2026-09-22T17:00:00Z",
        )
        self.assertEqual(self.client.get(reverse("lesson_occurrence_detail", args=[occurrence.pk])).status_code, 404)

    def test_non_manager_cannot_add_enrollment_or_generate_schedule(self):
        user = User.objects.create_user(username="seriesrider", password="test-pass")
        user.profile.team = self.team
        user.profile.role = "rider"
        user.profile.save()
        self.client.login(username="seriesrider", password="test-pass")
        self.assertEqual(self.client.get(reverse("lesson_enrollment_create", args=[self.series.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("lesson_series_generate", args=[self.series.pk])).status_code, 403)
