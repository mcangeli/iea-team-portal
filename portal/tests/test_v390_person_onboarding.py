from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.people import IEAParticipant, LegacyPersonLink, OrganizationRoleAssignment, Person, PersonRelationship
from portal.models import Rider, RiderGuardian, Season, SeasonClass, SeasonMembership, Team, UserProfile


class V390PersonOnboardingTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Unified Onboarding")
        self.season = Season.objects.create(
            team=self.team, name="2026-2027", start_date=date(2026, 8, 1),
            end_date=date(2027, 6, 30), is_active=True,
        )
        self.season_class = SeasonClass.objects.create(
            season=self.season, name="Upper Open", class_code="H1",
            team_level=SeasonClass.TeamLevel.UPPER, discipline="hunt_seat", active=True,
        )
        self.admin = User.objects.create_user(username="people-admin", password="test-pass")
        self.admin.profile.team = self.team
        self.admin.profile.role = UserProfile.Role.ADMIN
        self.admin.profile.save(update_fields=["team", "role"])
        self.client.force_login(self.admin)

    def test_create_person_can_assign_multiple_involvements_without_legacy_rider(self):
        response = self.client.post(reverse("person_create"), {
            "first_name": "Jordan",
            "last_name": "Multi Role",
            "email": "jordan@example.com",
            "active": "on",
            "involvement": [
                OrganizationRoleAssignment.Role.RIDER,
                OrganizationRoleAssignment.Role.PARENT_GUARDIAN,
            ],
        })

        self.assertEqual(response.status_code, 302)
        person = Person.objects.get(first_name="Jordan", last_name="Multi Role")
        self.assertFalse(hasattr(person, "legacy_identity"))
        self.assertSetEqual(
            set(person.role_assignments.filter(active=True).values_list("role", flat=True)),
            {
                OrganizationRoleAssignment.Role.RIDER,
                OrganizationRoleAssignment.Role.PARENT_GUARDIAN,
            },
        )

    def test_create_person_can_add_iea_participation_without_legacy_rider(self):
        response = self.client.post(reverse("person_create"), {
            "first_name": "Avery",
            "last_name": "IEA",
            "active": "on",
            "involvement": [OrganizationRoleAssignment.Role.RIDER],
            "iea_season": self.season.pk,
            "iea_team_level": SeasonMembership.TeamLevel.UPPER,
            "iea_classes": [self.season_class.pk],
        })

        self.assertEqual(response.status_code, 302)
        person = Person.objects.get(first_name="Avery", last_name="IEA")
        participant = IEAParticipant.objects.get(person=person, team=self.team)
        membership = SeasonMembership.objects.get(
            season=self.season, iea_participant=participant
        )
        self.assertIsNone(participant.legacy_rider_id)
        self.assertIsNone(membership.rider_id)
        self.assertEqual(membership.team_level, SeasonMembership.TeamLevel.UPPER)
        self.assertEqual(list(membership.classes.all()), [self.season_class])

    def test_rider_list_routes_new_identity_creation_to_people(self):
        response = self.client.get(reverse("rider_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("person_create"))
        self.assertNotContains(response, 'href="' + reverse("rider_create") + '"')

    def test_primary_navigation_exposes_add_person(self):
        response = self.client.get(reverse("people_directory"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("person_create"))


    def test_link_existing_parent_creates_canonical_person_relationship(self):
        rider_person = Person.objects.create(team=self.team, first_name="Casey", last_name="Rider")
        legacy_rider = Rider.objects.create(team=self.team, first_name="Casey", last_name="Rider")
        LegacyPersonLink.objects.create(person=rider_person, rider=legacy_rider)
        parent = Person.objects.create(team=self.team, first_name="Morgan", last_name="Parent")

        response = self.client.post(reverse("rider_guardian_link", args=[legacy_rider.pk]), {
            "person": f"person:{parent.pk}",
            "relationship": "Mother",
            "primary_contact": "on",
        })

        self.assertEqual(response.status_code, 302)
        relationship = PersonRelationship.objects.get(
            from_person=parent,
            to_person=rider_person,
            relationship_type=PersonRelationship.RelationshipType.PARENT_GUARDIAN,
        )
        self.assertEqual(relationship.label, "Mother")
        self.assertTrue(relationship.primary_contact)
        self.assertFalse(RiderGuardian.objects.filter(rider=legacy_rider).exists())

    def test_link_parent_page_offers_people_not_guardian_contacts(self):
        rider_person = Person.objects.create(team=self.team, first_name="Taylor", last_name="Rider")
        legacy_rider = Rider.objects.create(team=self.team, first_name="Taylor", last_name="Rider")
        LegacyPersonLink.objects.create(person=rider_person, rider=legacy_rider)
        parent = Person.objects.create(team=self.team, first_name="Alex", last_name="Parent", email="alex@example.com")

        response = self.client.get(reverse("rider_guardian_link", args=[legacy_rider.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alex Parent")
        self.assertContains(response, 'value="person:' + str(parent.pk) + '"')


    def test_person_profile_can_create_iea_membership_without_legacy_rider(self):
        person = Person.objects.create(team=self.team, first_name="Jordan", last_name="Rider")
        response = self.client.post(reverse("person_iea_membership_edit", args=[person.pk]), {
            "team_level": SeasonMembership.TeamLevel.FUTURES,
            "classes": [],
            "notes": "Person-native assignment",
        })
        self.assertEqual(response.status_code, 302)
        participant = IEAParticipant.objects.get(person=person, team=self.team)
        membership = SeasonMembership.objects.get(season=self.season, iea_participant=participant)
        self.assertIsNone(membership.rider_id)
        self.assertEqual(membership.team_level, SeasonMembership.TeamLevel.FUTURES)
        self.assertTrue(OrganizationRoleAssignment.objects.filter(
            team=self.team, person=person, role=OrganizationRoleAssignment.Role.RIDER, active=True
        ).exists())

    def test_person_profile_lists_iea_season_assignment(self):
        person = Person.objects.create(team=self.team, first_name="Avery", last_name="Rider")
        participant = IEAParticipant.objects.create(team=self.team, person=person)
        SeasonMembership.objects.create(season=self.season, iea_participant=participant, team_level=SeasonMembership.TeamLevel.UPPER)
        response = self.client.get(reverse("person_detail", args=[person.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "IEA PARTICIPATION")
        self.assertContains(response, "2026-2027")
        self.assertContains(response, "Upper School")


    def test_rider_family_card_uses_canonical_person_relationship_actions(self):
        rider = Rider.objects.create(team=self.team, first_name="Casey", last_name="Rider", active=True)
        rider_person = Person.objects.create(team=self.team, first_name="Casey", last_name="Rider")
        LegacyPersonLink.objects.create(person=rider_person, rider=rider)
        parent = Person.objects.create(team=self.team, first_name="Alex", last_name="Parent")
        relationship = PersonRelationship.objects.create(
            from_person=parent,
            to_person=rider_person,
            relationship_type=PersonRelationship.RelationshipType.PARENT_GUARDIAN,
            active=True,
        )

        response = self.client.get(reverse("rider_detail", args=[rider.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse("person_relationship_edit", args=[parent.pk, relationship.pk]),
        )
        self.assertContains(response, reverse("person_login_create", args=[parent.pk]))
        self.assertNotContains(response, "Unlink from rider")


    def test_parent_directory_uses_person_relationship_without_legacy_guardian(self):
        rider_person = Person.objects.create(team=self.team, first_name="Taylor", last_name="Rider")
        parent = Person.objects.create(
            team=self.team, first_name="Jordan", last_name="Parent",
            email="jordan@example.com", phone="555-0199",
        )
        PersonRelationship.objects.create(
            from_person=parent,
            to_person=rider_person,
            relationship_type=PersonRelationship.RelationshipType.PARENT_GUARDIAN,
            label="Parent",
            active=True,
        )

        response = self.client.get(reverse("parent_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, parent.display_name)
        self.assertContains(response, rider_person.display_name)
        self.assertContains(response, reverse("person_detail", args=[parent.pk]))
        self.assertContains(response, reverse("person_login_create", args=[parent.pk]))

    def test_parent_export_uses_person_relationship_without_legacy_guardian(self):
        rider_person = Person.objects.create(team=self.team, first_name="Taylor", last_name="Export Rider")
        parent = Person.objects.create(
            team=self.team, first_name="Jordan", last_name="Export Parent",
            email="export-parent@example.com", phone="555-0188",
        )
        PersonRelationship.objects.create(
            from_person=parent,
            to_person=rider_person,
            relationship_type=PersonRelationship.RelationshipType.PARENT_GUARDIAN,
            label="Guardian",
            active=True,
        )

        response = self.client.get(reverse("parent_export"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn(parent.display_name, content)
        self.assertIn(rider_person.display_name, content)
        self.assertIn("Guardian", content)
