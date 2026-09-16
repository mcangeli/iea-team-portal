from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase

from portal.forms_lessons_v340 import IEALessonSeriesForm, LessonSeriesForm
from portal.model_modules.lessons import LessonProgram
from portal.model_modules.people import OrganizationRoleAssignment, Person
from portal.models import Season, Team


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
