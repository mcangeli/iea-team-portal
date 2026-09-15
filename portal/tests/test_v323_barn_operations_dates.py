from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from portal.model_modules.barn_participation import HorsePersonRelationship
from portal.model_modules.horses import Horse
from portal.model_modules.people import OrganizationRoleAssignment, Person
from portal.models import Team, UserProfile


class V323BarnOperationsDateTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
        self.admin = User.objects.create_user(username="barn-ops-admin")
        profile = self.admin.profile
        profile.team = self.team
        profile.role = UserProfile.Role.ADMIN
        profile.save(update_fields=["team", "role"])
        self.person = Person.objects.create(team=self.team, first_name="Morgan", last_name="Barn")
        self.role = OrganizationRoleAssignment.objects.create(team=self.team, person=self.person, role=OrganizationRoleAssignment.Role.BOARDER, active=True)
        self.horse = Horse.objects.create(team=self.team, name="North Star")
        self.horse_link = HorsePersonRelationship.objects.create(team=self.team, horse=self.horse, person=self.person, relationship_type=HorsePersonRelationship.RelationshipType.BOARDER, active=True)
        self.client.force_login(self.admin)

    def _operations(self):
        return self.client.get(reverse("barn_operations"))

    def test_current_role_and_horse_relationship_are_shown(self):
        response = self._operations()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Morgan Barn")
        self.assertContains(response, "North Star")

    def test_future_role_assignment_is_not_current(self):
        self.role.start_date = timezone.localdate() + timedelta(days=1)
        self.role.save(update_fields=["start_date"])
        self.assertNotContains(self._operations(), "Morgan Barn")

    def test_role_assignment_ending_today_is_not_current(self):
        self.role.end_date = timezone.localdate()
        self.role.save(update_fields=["end_date"])
        self.assertNotContains(self._operations(), "Morgan Barn")

    def test_role_assignment_with_future_end_date_remains_current(self):
        self.role.end_date = timezone.localdate() + timedelta(days=1)
        self.role.save(update_fields=["end_date"])
        self.assertContains(self._operations(), "Morgan Barn")

    def test_future_horse_relationship_is_not_shown(self):
        self.horse_link.start_date = timezone.localdate() + timedelta(days=1)
        self.horse_link.save(update_fields=["start_date"])
        response = self._operations()
        self.assertContains(response, "Morgan Barn")
        self.assertNotContains(response, "North Star")

    def test_horse_relationship_ending_today_is_not_shown(self):
        self.horse_link.end_date = timezone.localdate()
        self.horse_link.save(update_fields=["end_date"])
        response = self._operations()
        self.assertContains(response, "Morgan Barn")
        self.assertNotContains(response, "North Star")

    def test_horse_relationship_with_future_end_date_remains_current(self):
        self.horse_link.end_date = timezone.localdate() + timedelta(days=1)
        self.horse_link.save(update_fields=["end_date"])
        self.assertContains(self._operations(), "North Star")
