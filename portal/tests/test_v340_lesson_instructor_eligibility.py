from datetime import date, datetime

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from portal.forms_lessons_v340 import IEALessonSeriesForm, LessonSeriesForm
from portal.model_modules.lessons import IEALessonSeriesContext, LessonAssignment, LessonOccurrence, LessonProgram, LessonSeries
from portal.model_modules.people import OrganizationRoleAssignment, Person
from portal.models import Season, SeasonMembership, Team


class LessonInstructorEligibilityTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Instructor Barn")
        self.program = LessonProgram.objects.create(team=self.team, name="General Lessons")
        self.iea_program = LessonProgram.objects.create(team=self.team, name="IEA Team Lessons")
        self.season = Season.objects.create(team=self.team, name="2026 IEA", start_date=date(2026, 8, 1), end_date=date(2027, 5, 31), is_active=True)
        self.coach = self._person("coach", profile_role="coach")
        self.trainer = self._person("trainer", person_role=OrganizationRoleAssignment.Role.TRAINER)
        self.assistant = self._person("assistant", person_role=OrganizationRoleAssignment.Role.ASSISTANT_TRAINER)
        self.rider = self._person("rider", person_role=OrganizationRoleAssignment.Role.RIDER)

    def _person(self, username, profile_role="rider", person_role=None):
        user = User.objects.create_user(username)
        user.profile.team = self.team
        user.profile.role = profile_role
        user.profile.save()
        person = Person.objects.create(team=self.team, user=user, first_name=username.title(), last_name="User")
        if person_role:
            OrganizationRoleAssignment.objects.create(team=self.team, person=person, role=person_role)
        return person

    def _starts_at(self):
        return timezone.make_aware(datetime(2026, 9, 28, 17, 0), timezone.get_current_timezone())

    def test_barn_series_offers_trainers_and_assistant_trainers_only(self):
        form = LessonSeriesForm(program=self.program)
        ids = set(form.fields["instructor"].queryset.values_list("pk", flat=True))
        self.assertEqual(ids, {self.trainer.pk, self.assistant.pk})

    def test_iea_series_offers_coaches_only(self):
        form = IEALessonSeriesForm(program=self.iea_program, season=self.season)
        ids = set(form.fields["instructor"].queryset.values_list("pk", flat=True))
        self.assertEqual(ids, {self.coach.pk})

    def test_rider_is_never_selectable_as_lesson_instructor(self):
        barn_form = LessonSeriesForm(program=self.program)
        iea_form = IEALessonSeriesForm(program=self.iea_program, season=self.season)
        self.assertNotIn(self.rider.pk, barn_form.fields["instructor"].queryset.values_list("pk", flat=True))
        self.assertNotIn(self.rider.pk, iea_form.fields["instructor"].queryset.values_list("pk", flat=True))

    def test_barn_series_rejects_rider_instructor_at_model_boundary(self):
        series = LessonSeries(program=self.program, name="Unsafe", instructor=self.rider)
        with self.assertRaises(ValidationError):
            series.full_clean()

    def test_barn_occurrence_rejects_rider_instructor_at_model_boundary(self):
        series = LessonSeries.objects.create(program=self.program, name="Safe", instructor=self.trainer)
        occurrence = LessonOccurrence(series=series, title="Unsafe occurrence", instructor=self.rider, starts_at=self._starts_at())
        with self.assertRaises(ValidationError):
            occurrence.full_clean()

    def test_instructor_assignment_rejects_rider(self):
        series = LessonSeries.objects.create(program=self.program, name="Assignment", instructor=self.trainer)
        occurrence = LessonOccurrence.objects.create(series=series, title="Assignment lesson", instructor=self.trainer, starts_at=self._starts_at())
        assignment = LessonAssignment(occurrence=occurrence, person=self.rider, role=LessonAssignment.Role.INSTRUCTOR)
        with self.assertRaises(ValidationError):
            assignment.full_clean()

    def test_iea_context_rejects_non_coach_series_instructor(self):
        series = LessonSeries.objects.create(program=self.iea_program, name="IEA unsafe", instructor=self.trainer)
        context = IEALessonSeriesContext(series=series, season=self.season, team_level=SeasonMembership.TeamLevel.UPPER)
        with self.assertRaises(ValidationError):
            context.full_clean()
