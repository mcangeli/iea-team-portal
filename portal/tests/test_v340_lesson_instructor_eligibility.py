from datetime import date, datetime, time

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
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
        self.second_coach = self._person("coach2", profile_role="coach")
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

    def _iea_form_data(self, *, instructor=None, team_level=SeasonMembership.TeamLevel.UPPER, name="Upper lessons"):
        return {
            "name": name,
            "instructor": (instructor or self.coach).pk,
            "team_level": team_level,
            "weekday": 1,
            "starts_at_time": "17:00",
            "duration_minutes": 60,
            "default_location": "Main ring",
            "capacity": 8,
            "start_date": "2026-09-01",
            "end_date": "2027-05-01",
            "active": "on",
            "notes": "",
        }

    def test_barn_series_offers_trainers_and_assistant_trainers_only(self):
        form = LessonSeriesForm(program=self.program)
        ids = set(form.fields["instructor"].queryset.values_list("pk", flat=True))
        self.assertEqual(ids, {self.trainer.pk, self.assistant.pk})

    def test_iea_series_offers_coaches_only(self):
        form = IEALessonSeriesForm(program=self.iea_program, season=self.season)
        ids = set(form.fields["instructor"].queryset.values_list("pk", flat=True))
        self.assertEqual(ids, {self.coach.pk, self.second_coach.pk})

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

    def test_new_iea_series_can_be_created_with_coach_instructor(self):
        form = IEALessonSeriesForm(self._iea_form_data(), program=self.iea_program, season=self.season)
        self.assertTrue(form.is_valid(), form.errors.as_json())
        series = form.save()
        self.assertEqual(series.instructor, self.coach)
        self.assertEqual(series.iea_context.season, self.season)
        self.assertEqual(series.iea_context.team_level, SeasonMembership.TeamLevel.UPPER)
        series.full_clean()
        series.iea_context.full_clean()

    def test_iea_series_edit_keeps_coach_queryset_and_updates_context(self):
        form = IEALessonSeriesForm(self._iea_form_data(), program=self.iea_program, season=self.season)
        self.assertTrue(form.is_valid(), form.errors.as_json())
        series = form.save()
        edit_form = IEALessonSeriesForm(instance=series, program=self.iea_program, season=self.season)
        ids = set(edit_form.fields["instructor"].queryset.values_list("pk", flat=True))
        self.assertEqual(ids, {self.coach.pk, self.second_coach.pk})
        self.assertEqual(edit_form.fields["team_level"].initial, SeasonMembership.TeamLevel.UPPER)

        data = self._iea_form_data(instructor=self.second_coach, team_level=SeasonMembership.TeamLevel.FUTURES, name=series.name)
        edit_form = IEALessonSeriesForm(data, instance=series, program=self.iea_program, season=self.season)
        self.assertTrue(edit_form.is_valid(), edit_form.errors.as_json())
        edited = edit_form.save()
        edited.refresh_from_db()
        edited.iea_context.refresh_from_db()
        self.assertEqual(edited.instructor, self.second_coach)
        self.assertEqual(edited.iea_context.team_level, SeasonMembership.TeamLevel.FUTURES)

    def test_iea_series_edit_view_uses_iea_aware_form(self):
        form = IEALessonSeriesForm(self._iea_form_data(), program=self.iea_program, season=self.season)
        self.assertTrue(form.is_valid(), form.errors.as_json())
        series = form.save()
        self.client.force_login(self.coach.user)
        response = self.client.get(reverse("lesson_series_edit", args=[series.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context["form"], IEALessonSeriesForm)
        ids = set(response.context["form"].fields["instructor"].queryset.values_list("pk", flat=True))
        self.assertEqual(ids, {self.coach.pk, self.second_coach.pk})
