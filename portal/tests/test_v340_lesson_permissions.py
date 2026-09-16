from datetime import date, time

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.lessons import IEALessonSeriesContext, LessonProgram, LessonSeries
from portal.model_modules.people import OrganizationRoleAssignment, Person
from portal.models import Season, SeasonMembership, Team
from portal.services.lesson_scheduling import create_manual_lesson_occurrence


class LessonDomainPermissionTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Permission Barn")
        self.admin = self._user("admin", "admin")
        self.coach = self._user("coach", "coach")
        self.trainer = self._user("trainer", "rider", OrganizationRoleAssignment.Role.TRAINER)
        self.assistant = self._user("assistant", "rider", OrganizationRoleAssignment.Role.ASSISTANT_TRAINER)
        self.rider = self._user("rider", "rider", OrganizationRoleAssignment.Role.RIDER)
        self.barn_program = LessonProgram.objects.create(team=self.team, name="Barn Lessons")
        self.barn_series = LessonSeries.objects.create(program=self.barn_program, name="Barn Tuesday", weekday=1, starts_at_time=time(17), duration_minutes=60, start_date=date(2026,9,1))
        self.barn_occurrence = create_manual_lesson_occurrence(self.barn_series, date(2026,9,22), time(17))
        self.season = Season.objects.create(team=self.team, name="2026 IEA", start_date=date(2026,8,1), end_date=date(2027,5,31), active=True)
        self.iea_program = LessonProgram.objects.create(team=self.team, name="IEA Team Lessons")
        self.iea_series = LessonSeries.objects.create(program=self.iea_program, name="Upper Team", weekday=3, starts_at_time=time(18), duration_minutes=60, start_date=date(2026,9,1))
        IEALessonSeriesContext.objects.create(series=self.iea_series, season=self.season, team_level=SeasonMembership.TeamLevel.UPPER)
        self.iea_occurrence = create_manual_lesson_occurrence(self.iea_series, date(2026,9,24), time(18))

    def _user(self, username, profile_role, person_role=None):
        user = User.objects.create_user(username, password="test")
        user.profile.team = self.team; user.profile.role = profile_role; user.profile.save()
        person = Person.objects.create(team=self.team, user=user, first_name=username.title(), last_name="User")
        if person_role: OrganizationRoleAssignment.objects.create(team=self.team, person=person, role=person_role)
        return user

    def _status(self, user, occurrence):
        self.client.force_login(user)
        return self.client.get(reverse("lesson_day_workspace", args=[occurrence.pk])).status_code

    def test_admin_can_manage_both_domains(self):
        self.assertEqual(self._status(self.admin, self.barn_occurrence), 200)
        self.assertEqual(self._status(self.admin, self.iea_occurrence), 200)

    def test_coach_can_manage_iea_but_not_barn(self):
        self.assertEqual(self._status(self.coach, self.iea_occurrence), 200)
        self.assertEqual(self._status(self.coach, self.barn_occurrence), 403)

    def test_trainer_can_manage_barn_but_not_iea(self):
        self.assertEqual(self._status(self.trainer, self.barn_occurrence), 200)
        self.assertEqual(self._status(self.trainer, self.iea_occurrence), 403)

    def test_assistant_trainer_can_manage_barn_but_not_iea(self):
        self.assertEqual(self._status(self.assistant, self.barn_occurrence), 200)
        self.assertEqual(self._status(self.assistant, self.iea_occurrence), 403)

    def test_rider_cannot_manage_lesson_day(self):
        self.assertEqual(self._status(self.rider, self.barn_occurrence), 403)
        self.assertEqual(self._status(self.rider, self.iea_occurrence), 403)
