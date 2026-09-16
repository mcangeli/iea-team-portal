from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from portal.horse_models import Horse, HorseIdentifier
from portal.model_modules.barn_participation import HorsePersonRelationship
from portal.model_modules.people import Person
from portal.models import Team, UserProfile


User = get_user_model()


class EquineRegistryUITests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="ArenaLine Test Program")
        self.admin = User.objects.create_user(username="equine-admin", password="test-pass")
        self.admin.profile.team = self.team
        self.admin.profile.role = UserProfile.Role.ADMIN
        self.admin.profile.save(update_fields=["team", "role"])
        self.horse = Horse.objects.create(team=self.team, name="Atlas")
        self.client.force_login(self.admin)

    def test_horse_detail_shows_registry_identifiers(self):
        HorseIdentifier.objects.create(
            horse=self.horse,
            authority="IEA",
            identifier_type="Horse ID",
            value="IEA-12345",
            is_primary=True,
        )
        response = self.client.get(reverse("horse_detail", args=[self.horse.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Registry identifiers")
        self.assertContains(response, "IEA-12345")
        self.assertContains(response, "Primary")

    def test_manager_can_add_identifier_from_horse_profile(self):
        response = self.client.post(
            reverse("horse_identifier_add", args=[self.horse.pk]),
            {
                "authority": "USEF",
                "identifier_type": "Registration",
                "value": "1234567",
                "is_primary": "on",
                "notes": "Imported from registry",
            },
        )
        self.assertRedirects(response, reverse("horse_detail", args=[self.horse.pk]))
        identifier = self.horse.identifiers.get()
        self.assertEqual(identifier.authority, "USEF")
        self.assertEqual(identifier.value, "1234567")

    def test_manager_can_edit_identifier(self):
        identifier = HorseIdentifier.objects.create(horse=self.horse, authority="IEA", value="OLD")
        response = self.client.post(
            reverse("horse_identifier_edit", args=[self.horse.pk, identifier.pk]),
            {
                "authority": "IEA",
                "identifier_type": "Horse ID",
                "value": "NEW",
                "notes": "Corrected",
            },
        )
        self.assertRedirects(response, reverse("horse_detail", args=[self.horse.pk]))
        identifier.refresh_from_db()
        self.assertEqual(identifier.value, "NEW")

    def test_horse_relationship_types_include_care_team_roles(self):
        values = dict(HorsePersonRelationship.RelationshipType.choices)
        self.assertEqual(values[HorsePersonRelationship.RelationshipType.VETERINARIAN], "Veterinarian")
        self.assertEqual(values[HorsePersonRelationship.RelationshipType.FARRIER], "Farrier")
        self.assertEqual(values[HorsePersonRelationship.RelationshipType.DENTIST], "Equine Dentist")
        self.assertEqual(values[HorsePersonRelationship.RelationshipType.EMERGENCY_CONTACT], "Emergency Contact")

    def test_care_team_relationship_uses_existing_person_record(self):
        person = Person.objects.create(team=self.team, first_name="Dana", last_name="Vet", active=True)
        relationship = HorsePersonRelationship.objects.create(
            team=self.team,
            horse=self.horse,
            person=person,
            relationship_type=HorsePersonRelationship.RelationshipType.VETERINARIAN,
        )
        self.assertEqual(relationship.person, person)
        response = self.client.get(reverse("horse_detail", args=[self.horse.pk]))
        self.assertContains(response, "Dana Vet")
        self.assertContains(response, "Veterinarian")
