from datetime import date, datetime, time

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from portal.model_modules.lessons import IEALessonSeriesContext, LessonProgram, LessonSeries
from portal.model_modules.people import OrganizationRoleAssignment, Person
from portal.models import Season, SeasonMembership, Team
from portal.services.lesson_scheduling import create_manual_lesson_occurrence


class LessonProgramUIPermissionTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Lesson UI Permission Barn")
        self.admin = self._user("admin", "admin")
        self.coach = self._user("coach", "coach")
        self.trainer = self._user("trainer", "rider", OrganizationRoleAssignment.Role.TRAINER)
        self.rider = self._user("rider", "rider", OrganizationRoleAssignment.Role.RIDER)
        self.barn_program = LessonProgram.objects.create(team=self.team, name="Barn Lessons")
        self.barn_series = LessonSeries.objects.create(program=self.barn_program, name="Barn Tuesday", weekday=1, starts_at_time=time(17), duration_minutes=60, start_date=date(2026, 9, 1))
        self.barn_occurrence = create_manual_lesson_occurrence(self.barn_series, starts_at=self._at(date(2026, 9, 22), time(17)))
        self.season = Season.objects.create(team=self.team, name="2026 IEA", start_date=date(2026, 8, 1), end_date=date(2027, 5, 31), is_active=True)
        self.iea_program = LessonProgram.objects.create(team=self.team, name="IEA Team Lessons")
        self.iea_series = LessonSeries.objects.create(program=self.iea_program, name="Upper Team", weekday=3, starts_at_time=time(18), duration_minutes=60, start_date=date(2026, 9, 1))
        IEALessonSeriesContext.objects.create(series=self.iea_series, season=self.season, team_level=SeasonMembership.TeamLevel.UPPER)
        self.iea_occurrence = create_manual_lesson_occurrence(self.iea_series, starts_at=self._at(date(2026, 9, 24), time(18)))

    def _user(self, username, profile_role, person_role=None):
        user = User.objects.create_user(username, password="test"); user.profile.team=self.team; user.profile.role=profile_role; user.profile.save()
        person=Person.objects.create(team=self.team,user=user,first_name=username.title(),last_name="User")
        if person_role: OrganizationRoleAssignment.objects.create(team=self.team,person=person,role=person_role)
        return user

    def _at(self, day, clock): return timezone.make_aware(datetime.combine(day,clock),timezone.get_current_timezone())
    def _get(self,user,name,*args): self.client.force_login(user); return self.client.get(reverse(name,args=args))
    def _post(self,user,name,*args): self.client.force_login(user); return self.client.post(reverse(name,args=args),{})

    def test_barn_program_management_is_trainer_domain(self):
        self.assertEqual(self._get(self.trainer,"lesson_program_edit",self.barn_program.pk).status_code,200)
        self.assertEqual(self._get(self.coach,"lesson_program_edit",self.barn_program.pk).status_code,403)
        self.assertEqual(self._get(self.admin,"lesson_program_edit",self.barn_program.pk).status_code,200)

    def test_iea_series_creation_is_coach_domain(self):
        self.assertEqual(self._get(self.coach,"iea_lesson_series_create").status_code,200)
        self.assertEqual(self._get(self.trainer,"iea_lesson_series_create").status_code,403)
        self.assertEqual(self._get(self.admin,"iea_lesson_series_create").status_code,200)

    def test_series_edit_uses_series_domain(self):
        self.assertEqual(self._get(self.trainer,"lesson_series_edit",self.barn_series.pk).status_code,200)
        self.assertEqual(self._get(self.coach,"lesson_series_edit",self.barn_series.pk).status_code,403)
        self.assertEqual(self._get(self.coach,"lesson_series_edit",self.iea_series.pk).status_code,200)
        self.assertEqual(self._get(self.trainer,"lesson_series_edit",self.iea_series.pk).status_code,403)

    def test_occurrence_operations_use_occurrence_domain(self):
        self.assertEqual(self._post(self.trainer,"lesson_occurrence_prepare",self.barn_occurrence.pk).status_code,302)
        self.assertEqual(self._post(self.coach,"lesson_occurrence_prepare",self.barn_occurrence.pk).status_code,403)
        self.assertEqual(self._post(self.coach,"lesson_occurrence_prepare",self.iea_occurrence.pk).status_code,302)
        self.assertEqual(self._post(self.trainer,"lesson_occurrence_prepare",self.iea_occurrence.pk).status_code,403)

    def test_read_pages_expose_domain_specific_can_manage(self):
        barn=self._get(self.trainer,"lesson_series_detail",self.barn_series.pk); self.assertTrue(barn.context["can_manage"])
        barn_coach=self._get(self.coach,"lesson_series_detail",self.barn_series.pk); self.assertFalse(barn_coach.context["can_manage"])
        iea=self._get(self.coach,"lesson_series_detail",self.iea_series.pk); self.assertTrue(iea.context["can_manage"])
        iea_trainer=self._get(self.trainer,"lesson_series_detail",self.iea_series.pk); self.assertFalse(iea_trainer.context["can_manage"])

    def test_rider_can_read_but_not_manage(self):
        self.assertEqual(self._get(self.rider,"lesson_series_detail",self.barn_series.pk).status_code,200)
        self.assertEqual(self._get(self.rider,"lesson_series_edit",self.barn_series.pk).status_code,403)
        self.assertEqual(self._get(self.rider,"lesson_occurrence_detail",self.iea_occurrence.pk).status_code,200)
        self.assertEqual(self._post(self.rider,"lesson_occurrence_prepare",self.iea_occurrence.pk).status_code,403)
