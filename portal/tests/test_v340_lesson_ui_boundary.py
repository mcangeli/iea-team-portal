from datetime import date, time

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.lessons import IEALessonSeriesContext, LessonProgram, LessonSeries
from portal.models import Season, Team


class LessonUIBoundaryTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="UI Boundary Barn")
        self.season = Season.objects.create(team=self.team, name="2026-2027", start_date=date(2026, 8, 1), end_date=date(2027, 6, 30), is_active=True)
        self.admin = User.objects.create_user(username="boundaryadmin", password="test-pass")
        self.admin.profile.team = self.team
        self.admin.profile.role = "admin"
        self.admin.profile.save()
        self.client.login(username="boundaryadmin", password="test-pass")
        self.barn_program = LessonProgram.objects.create(team=self.team, name="Barn Academy")
        self.barn_series = LessonSeries.objects.create(program=self.barn_program, name="Barn Intermediate", weekday=1, starts_at_time=time(17, 0), duration_minutes=60)
        self.iea_program = LessonProgram.objects.create(team=self.team, name="IEA Team Lessons")
        self.futures_series = LessonSeries.objects.create(program=self.iea_program, name="Futures Practice", weekday=2, starts_at_time=time(17, 0), duration_minutes=60)
        self.upper_series = LessonSeries.objects.create(program=self.iea_program, name="Upper Practice", weekday=3, starts_at_time=time(18, 0), duration_minutes=60)
        IEALessonSeriesContext.objects.create(series=self.futures_series, season=self.season, team_level="futures")
        IEALessonSeriesContext.objects.create(series=self.upper_series, season=self.season, team_level="upper")

    def test_barn_directory_does_not_show_iea_program(self):
        response = self.client.get(reverse("lesson_program_list"))
        self.assertContains(response, "Barn Academy")
        self.assertNotContains(response, "IEA Team Lessons")

    def test_iea_workspace_separates_futures_and_upper(self):
        response = self.client.get(reverse("iea_lesson_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Futures lesson series")
        self.assertContains(response, "Futures Practice")
        self.assertContains(response, "Upper lesson series")
        self.assertContains(response, "Upper Practice")

    def test_iea_series_detail_has_team_membership_roster_language(self):
        response = self.client.get(reverse("lesson_series_detail", args=[self.upper_series.pk]))
        self.assertContains(response, "Team membership")
        self.assertContains(response, "season membership")
        self.assertNotContains(response, "Add enrollment")

    def test_barn_series_detail_retains_enrollment_workflow(self):
        response = self.client.get(reverse("lesson_series_detail", args=[self.barn_series.pk]))
        self.assertContains(response, "Enrollments")
        self.assertContains(response, "Add enrollment")
        self.assertNotContains(response, "season membership")

    def test_iea_series_rejects_enrollment_ui(self):
        response = self.client.get(reverse("lesson_enrollment_create", args=[self.upper_series.pk]))
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_iea_series_for_active_season_and_level(self):
        response = self.client.post(reverse("iea_lesson_series_create"), {
            "name": "Upper Conditioning",
            "team_level": "upper",
            "weekday": 4,
            "starts_at_time": "18:30",
            "duration_minutes": 60,
            "start_date": "2026-09-01",
            "end_date": "2027-05-31",
            "active": "on",
        })
        self.assertEqual(response.status_code, 302)
        series = LessonSeries.objects.get(name="Upper Conditioning")
        self.assertEqual(series.iea_context.season, self.season)
        self.assertEqual(series.iea_context.team_level, "upper")

    def test_iea_workspace_is_active_season_scoped(self):
        old_season = Season.objects.create(team=self.team, name="2025-2026", start_date=date(2025, 8, 1), end_date=date(2026, 6, 30))
        old_series = LessonSeries.objects.create(program=self.iea_program, name="Old Upper Practice")
        IEALessonSeriesContext.objects.create(series=old_series, season=old_season, team_level="upper")
        response = self.client.get(reverse("iea_lesson_list"))
        self.assertNotContains(response, "Old Upper Practice")
        self.assertContains(response, "Upper Practice")
