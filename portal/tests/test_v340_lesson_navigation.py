from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.people import OrganizationRoleAssignment, Person
from portal.models import Team


class LessonNavigationCapabilityTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Navigation Barn")
        self.admin = self._user("admin", "admin")
        self.coach = self._user("coach", "coach")
        self.trainer = self._user("trainer", "rider", [OrganizationRoleAssignment.Role.TRAINER])
        self.rider = self._user("rider", "rider", [OrganizationRoleAssignment.Role.RIDER])
        self.trainer_rider = self._user("trainer_rider", "rider", [OrganizationRoleAssignment.Role.TRAINER, OrganizationRoleAssignment.Role.RIDER])
        self.coach_rider = self._user("coach_rider", "coach", [OrganizationRoleAssignment.Role.RIDER])

    def _user(self, username, profile_role, person_roles=None):
        user = User.objects.create_user(username, password="test")
        user.profile.team = self.team
        user.profile.role = profile_role
        user.profile.save()
        person = Person.objects.create(team=self.team, user=user, first_name=username.title(), last_name="User")
        for role in person_roles or []:
            OrganizationRoleAssignment.objects.create(team=self.team, person=person, role=role)
        return user

    def _home(self, user):
        self.client.force_login(user)
        return self.client.get(reverse("dashboard"))

    def test_plain_rider_sees_only_personal_lesson_navigation(self):
        response = self._home(self.rider)
        self.assertContains(response, "My lessons")
        self.assertNotContains(response, "Barn lesson programs")
        self.assertNotContains(response, ">Team lessons<", html=False)

    def test_trainer_rider_sees_barn_management_and_personal_lessons(self):
        response = self._home(self.trainer_rider)
        self.assertContains(response, "Barn lesson programs")
        self.assertContains(response, "My lessons")
        self.assertNotContains(response, ">Team lessons<", html=False)

    def test_coach_rider_sees_iea_management_and_personal_lessons(self):
        response = self._home(self.coach_rider)
        self.assertContains(response, "Team lessons")
        self.assertContains(response, "My lessons")
        self.assertNotContains(response, "Barn lesson programs")

    def test_trainer_without_canonical_rider_role_keeps_legacy_rider_compatibility(self):
        response = self._home(self.trainer)
        self.assertContains(response, "Barn lesson programs")
        self.assertContains(response, "My lessons")
        self.assertNotContains(response, ">Team lessons<", html=False)

    def test_coach_sees_iea_management_not_barn_management(self):
        response = self._home(self.coach)
        self.assertContains(response, "Team lessons")
        self.assertNotContains(response, "Barn lesson programs")
        self.assertNotContains(response, "My lessons")

    def test_admin_sees_both_management_domains(self):
        response = self._home(self.admin)
        self.assertContains(response, "Team lessons")
        self.assertContains(response, "Barn lesson programs")
        self.assertNotContains(response, "My lessons")
