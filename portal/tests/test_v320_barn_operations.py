from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.horse_models import Horse
from portal.model_modules.barn_participation import HorsePersonRelationship
from portal.model_modules.people import OrganizationRoleAssignment, Person
from portal.models import Team, UserProfile


class V320BarnOperationsTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
        self.other_team = Team.objects.create(name="Other Barn")

        self.member = User.objects.create_user(username="ops-member", password="pass12345")
        self.member.profile.team = self.team
        self.member.profile.role = UserProfile.Role.PARENT
        self.member.profile.save(update_fields=["team", "role"])

        self.trainer = Person.objects.create(team=self.team, first_name="Taylor", last_name="Trainer")
        OrganizationRoleAssignment.objects.create(
            team=self.team,
            person=self.trainer,
            role=OrganizationRoleAssignment.Role.TRAINER,
        )
        self.horse = Horse.objects.create(team=self.team, name="Jasper")
        HorsePersonRelationship.objects.create(
            team=self.team,
            horse=self.horse,
            person=self.trainer,
            relationship_type=HorsePersonRelationship.RelationshipType.TRAINER,
        )

        self.outsider = Person.objects.create(team=self.other_team, first_name="Outside", last_name="Staff")
        OrganizationRoleAssignment.objects.create(
            team=self.other_team,
            person=self.outsider,
            role=OrganizationRoleAssignment.Role.BARN_STAFF,
        )

    def test_authenticated_member_can_view_operations_roster(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("barn_operations"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Operations roster")
        self.assertContains(response, "Taylor Trainer")
        self.assertContains(response, "Training team")

    def test_operations_roster_surfaces_active_horse_responsibilities(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("barn_operations"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Jasper")
        self.assertContains(response, "Trainer")
        self.assertContains(response, reverse("horse_detail", args=[self.horse.pk]))

    def test_operations_roster_is_tenant_scoped(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("barn_operations"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Outside Staff")
