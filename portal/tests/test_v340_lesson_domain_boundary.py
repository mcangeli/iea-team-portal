from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase

from portal.model_modules.lessons import IEALessonSeriesContext, LessonEnrollment, LessonProgram, LessonSeries
from portal.model_modules.people import Person
from portal.models import Season, Team


class LessonDomainBoundaryTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Boundary Barn")
        self.season = Season.objects.create(
            team=self.team, name="2026-2027", start_date=date(2026, 8, 1), end_date=date(2027, 6, 30), is_active=True
        )
        self.program = LessonProgram.objects.create(team=self.team, name="Shared Lesson Engine")
        self.barn_series = LessonSeries.objects.create(program=self.program, name="Barn Intermediate")
        self.iea_series = LessonSeries.objects.create(program=self.program, name="Upper Team Practice")
        self.person = Person.objects.create(team=self.team, first_name="Riley", last_name="Student")

    def test_generic_series_is_barn_series_without_iea_context(self):
        self.assertFalse(self.barn_series.is_iea_series)

    def test_iea_context_marks_generic_series_as_iea_specialization(self):
        IEALessonSeriesContext.objects.create(
            series=self.iea_series, season=self.season, team_level=IEALessonSeriesContext.TeamLevel.UPPER
        )
        self.assertTrue(self.iea_series.is_iea_series)
        self.assertEqual(self.iea_series.iea_context.season, self.season)
        self.assertEqual(self.iea_series.iea_context.team_level, "upper")

    def test_iea_context_supports_futures_and_upper_only(self):
        context = IEALessonSeriesContext(series=self.iea_series, season=self.season, team_level="both")
        with self.assertRaises(ValidationError):
            context.full_clean()

    def test_iea_context_must_remain_in_same_organization(self):
        other_team = Team.objects.create(name="Other Barn")
        other_season = Season.objects.create(
            team=other_team, name="2026-2027", start_date=date(2026, 8, 1), end_date=date(2027, 6, 30)
        )
        context = IEALessonSeriesContext(series=self.iea_series, season=other_season, team_level="upper")
        with self.assertRaises(ValidationError):
            context.full_clean()

    def test_barn_series_accepts_general_lesson_enrollment(self):
        enrollment = LessonEnrollment(series=self.barn_series, person=self.person)
        enrollment.full_clean()
        enrollment.save()
        self.assertEqual(self.barn_series.enrollments.count(), 1)

    def test_iea_series_rejects_general_barn_enrollment(self):
        IEALessonSeriesContext.objects.create(
            series=self.iea_series, season=self.season, team_level=IEALessonSeriesContext.TeamLevel.FUTURES
        )
        enrollment = LessonEnrollment(series=self.iea_series, person=self.person)
        with self.assertRaisesMessage(ValidationError, "season team membership"):
            enrollment.full_clean()

    def test_iea_context_is_one_to_one_with_series(self):
        IEALessonSeriesContext.objects.create(
            series=self.iea_series, season=self.season, team_level=IEALessonSeriesContext.TeamLevel.UPPER
        )
        duplicate = IEALessonSeriesContext(
            series=self.iea_series, season=self.season, team_level=IEALessonSeriesContext.TeamLevel.FUTURES
        )
        with self.assertRaises(ValidationError):
            duplicate.full_clean()
