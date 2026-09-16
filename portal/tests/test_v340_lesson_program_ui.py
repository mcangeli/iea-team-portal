from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.lessons import LessonProgram, LessonSeries
from portal.models import Team


class LessonProgramUITests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="UI Barn")
        self.admin = User.objects.create_user(username="lessonadmin", password="test-pass")
        self.admin.profile.team = self.team
        self.admin.profile.role = "admin"
        self.admin.profile.save()
        self.client.login(username="lessonadmin", password="test-pass")
        self.program = LessonProgram.objects.create(team=self.team, name="Academy Lessons", default_capacity=6)

    def test_program_directory_renders(self):
        response = self.client.get(reverse("lesson_program_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lesson Programs")
        self.assertContains(response, "Academy Lessons")

    def test_program_detail_renders_series(self):
        LessonSeries.objects.create(program=self.program, name="Tuesday Intermediate")
        response = self.client.get(reverse("lesson_program_detail", args=[self.program.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tuesday Intermediate")

    def test_admin_can_create_program(self):
        response = self.client.post(reverse("lesson_program_create"), {
            "name": "Beginner Academy",
            "default_capacity": 8,
            "active": "on",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(LessonProgram.objects.filter(team=self.team, name="Beginner Academy").exists())

    def test_admin_can_create_series(self):
        response = self.client.post(reverse("lesson_series_create", args=[self.program.pk]), {
            "name": "Wednesday Foundations",
            "weekday": 2,
            "starts_at_time": "17:30",
            "duration_minutes": 60,
            "default_location": "Indoor Arena",
            "capacity": 5,
            "active": "on",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(LessonSeries.objects.filter(program=self.program, name="Wednesday Foundations").exists())

    def test_program_detail_is_organization_scoped(self):
        other_team = Team.objects.create(name="Other Barn")
        other_program = LessonProgram.objects.create(team=other_team, name="Private Program")
        response = self.client.get(reverse("lesson_program_detail", args=[other_program.pk]))
        self.assertEqual(response.status_code, 404)

    def test_program_create_requires_management_access(self):
        user = User.objects.create_user(username="rideruser", password="test-pass")
        user.profile.team = self.team
        user.profile.role = "rider"
        user.profile.save()
        self.client.login(username="rideruser", password="test-pass")
        response = self.client.get(reverse("lesson_program_create"))
        self.assertEqual(response.status_code, 403)
