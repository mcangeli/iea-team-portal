from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.barn_participation import HorsePersonRelationship
from portal.model_modules.horses import Horse
from portal.model_modules.people import Person
from portal.models import Team, UserProfile


class V320BarnParticipationUITests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
        self.other_team = Team.objects.create(name="Other Barn")

        self.admin = User.objects.create_user(username="barn-admin-v320", password="pass12345")
        self.admin.profile.team = self.team
        self.admin.profile.role = UserProfile.Role.ADMIN
        self.admin.profile.save(update_fields=["team", "role"])

        self.member = User.objects.create_user(username="barn-member-v320", password="pass12345")
        self.member.profile.team = self.team
        self.member.profile.role = UserProfile.Role.RIDER
        self.member.profile.save(update_fields=["team", "role"])

        self.person = Person.objects.create(team=self.team, user=self.member, first_name="Jamie", last_name="Rider")
        self.horse = Horse.objects.create(team=self.team, name="Jasper")
        self.outsider = Person.objects.create(team=self.other_team, first_name="Outside", last_name="Person")

    def test_manager_can_add_horse_person_relationship(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("horse_person_relationship_add", args=[self.horse.pk]),
            {
                "person": self.person.pk,
                "relationship_type": HorsePersonRelationship.RelationshipType.HALF_LEASE,
                "share_percent": 50,
                "active": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        relationship = HorsePersonRelationship.objects.get(horse=self.horse, person=self.person)
        self.assertEqual(relationship.relationship_type, HorsePersonRelationship.RelationshipType.HALF_LEASE)
        self.assertEqual(relationship.share_percent, 50)

    def test_non_manager_cannot_manage_horse_person_relationships(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("horse_person_relationship_add", args=[self.horse.pk]))
        self.assertEqual(response.status_code, 403)

    def test_relationship_form_rejects_other_organization_person(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("horse_person_relationship_add", args=[self.horse.pk]),
            {
                "person": self.outsider.pk,
                "relationship_type": HorsePersonRelationship.RelationshipType.OWNER,
                "active": "on",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Select a valid choice")
        self.assertFalse(HorsePersonRelationship.objects.filter(horse=self.horse).exists())

    def test_horse_and_person_profiles_show_same_relationship(self):
        relationship = HorsePersonRelationship.objects.create(
            team=self.team,
            horse=self.horse,
            person=self.person,
            relationship_type=HorsePersonRelationship.RelationshipType.TRAINER,
        )
        self.client.force_login(self.admin)

        horse_response = self.client.get(reverse("horse_detail", args=[self.horse.pk]))
        self.assertEqual(horse_response.status_code, 200)
        self.assertContains(horse_response, "Jamie Rider")
        self.assertContains(horse_response, "Trainer")
        self.assertContains(horse_response, reverse("horse_person_relationship_edit", args=[self.horse.pk, relationship.pk]))

        person_response = self.client.get(reverse("person_detail", args=[self.person.pk]))
        self.assertEqual(person_response.status_code, 200)
        self.assertContains(person_response, "Jasper")
        self.assertContains(person_response, "Trainer")
        self.assertContains(person_response, reverse("horse_detail", args=[self.horse.pk]))
