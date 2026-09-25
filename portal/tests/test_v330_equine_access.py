from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from portal.horse_models import Horse
from portal.model_modules.barn_participation import HorsePersonRelationship
from portal.model_modules.capabilities import OrganizationCapabilityAssignment
from portal.model_modules.people import Person
from portal.models import Team, UserProfile


User = get_user_model()


class EquineAccessTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="ArenaLine Access")
        self.admin = self._user("access-admin", UserProfile.Role.ADMIN)
        self.boarder_user = self._user("access-boarder", UserProfile.Role.PARENT)
        self.delegate_user = self._user("access-delegate", UserProfile.Role.PARENT)
        self.other_user = self._user("access-other", UserProfile.Role.PARENT)
        self.boarder = Person.objects.create(team=self.team, user=self.boarder_user, first_name="Bailey", last_name="Boarder")
        self.delegate = Person.objects.create(team=self.team, user=self.delegate_user, first_name="Morgan", last_name="Delegate")
        self.other_person = Person.objects.create(team=self.team, user=self.other_user, first_name="Riley", last_name="Other")
        self.horse = Horse.objects.create(team=self.team, name="Atlas")
        self.other_horse = Horse.objects.create(team=self.team, name="Comet")
        self.relationship = HorsePersonRelationship.objects.create(
            team=self.team,
            horse=self.horse,
            person=self.boarder,
            relationship_type=HorsePersonRelationship.RelationshipType.BOARDER,
            start_date=timezone.localdate(),
            active=True,
        )

    def _user(self, username, role):
        user = User.objects.create_user(username=username, password="test-pass-123")
        user.profile.team = self.team
        user.profile.role = role
        user.profile.save(update_fields=["team", "role"])
        return user

    def _grant_manage_horses(self):
        return OrganizationCapabilityAssignment.objects.create(
            team=self.team,
            person=self.delegate,
            capability=OrganizationCapabilityAssignment.Capability.MANAGE_HORSES,
            start_date=timezone.localdate(),
            active=True,
        )

    def test_current_boarder_can_edit_related_horse(self):
        self.client.force_login(self.boarder_user)
        response = self.client.get(reverse("horse_edit", args=[self.horse.pk]))
        self.assertEqual(response.status_code, 200)

    def test_current_boarder_can_manage_related_horse_care_documents_and_coggins(self):
        self.client.force_login(self.boarder_user)
        for route in (
            reverse("horse_care_add", args=[self.horse.pk]),
            reverse("horse_document_add", args=[self.horse.pk]),
            reverse("horse_coggins_add", args=[self.horse.pk]),
            reverse("horse_identifier_add", args=[self.horse.pk]),
        ):
            with self.subTest(route=route):
                self.assertEqual(self.client.get(route).status_code, 200)

    def test_boarder_cannot_manage_unrelated_horse(self):
        self.client.force_login(self.boarder_user)
        self.assertEqual(self.client.get(reverse("horse_edit", args=[self.other_horse.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("horse_document_add", args=[self.other_horse.pk])).status_code, 403)

    def test_ended_boarder_relationship_removes_access(self):
        self.relationship.end_date = timezone.localdate()
        self.relationship.save(update_fields=["end_date"])
        self.client.force_login(self.boarder_user)
        self.assertEqual(self.client.get(reverse("horse_edit", args=[self.horse.pk])).status_code, 403)

    def test_inactive_boarder_relationship_removes_access(self):
        self.relationship.active = False
        self.relationship.save(update_fields=["active"])
        self.client.force_login(self.boarder_user)
        self.assertEqual(self.client.get(reverse("horse_edit", args=[self.horse.pk])).status_code, 403)

    def test_boarder_cannot_change_relationships_or_season_eligibility(self):
        self.client.force_login(self.boarder_user)
        self.assertEqual(self.client.get(reverse("horse_person_relationship_add", args=[self.horse.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("horse_season_profile", args=[self.horse.pk])).status_code, 403)

    def test_boarder_profile_exposes_record_controls_but_not_structure_controls(self):
        self.client.force_login(self.boarder_user)
        response = self.client.get(reverse("horse_detail", args=[self.horse.pk]))
        self.assertContains(response, "Edit horse")
        self.assertContains(response, "Record care")
        self.assertNotContains(
            response,
            reverse("horse_person_relationship_add", args=[self.horse.pk]),
        )
        self.assertNotContains(
            response,
            reverse("horse_season_profile", args=[self.horse.pk]),
        )

    def test_explicit_manage_horses_capability_is_organization_wide(self):
        self._grant_manage_horses()
        self.client.force_login(self.delegate_user)
        self.assertEqual(self.client.get(reverse("horse_edit", args=[self.horse.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("horse_edit", args=[self.other_horse.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("horse_create")).status_code, 200)

    def test_explicit_capability_does_not_grant_structure_or_compliance_configuration(self):
        self._grant_manage_horses()
        self.client.force_login(self.delegate_user)
        self.assertEqual(self.client.get(reverse("horse_person_relationship_add", args=[self.horse.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("horse_season_profile", args=[self.horse.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("horse_compliance_requirements")).status_code, 403)

    def test_ended_explicit_capability_removes_access(self):
        assignment = self._grant_manage_horses()
        assignment.end_date = timezone.localdate()
        assignment.save(update_fields=["end_date"])
        self.client.force_login(self.delegate_user)
        self.assertEqual(self.client.get(reverse("horse_edit", args=[self.horse.pk])).status_code, 403)

    def test_admin_can_manage_horse_capability_from_person_profile(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("person_horse_access", args=[self.delegate.pk]), {
            "active": "on",
            "start_date": timezone.localdate().isoformat(),
            "end_date": "",
            "notes": "Equine care coordinator",
        })
        self.assertRedirects(response, reverse("person_detail", args=[self.delegate.pk]))
        assignment = OrganizationCapabilityAssignment.objects.get(person=self.delegate)
        self.assertEqual(assignment.capability, OrganizationCapabilityAssignment.Capability.MANAGE_HORSES)
        self.assertTrue(assignment.active)

    def test_non_people_manager_cannot_delegate_horse_capability(self):
        self.client.force_login(self.boarder_user)
        response = self.client.get(reverse("person_horse_access", args=[self.delegate.pk]))
        self.assertEqual(response.status_code, 403)
