from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.people import (
    LegacyPersonLink,
    OrganizationRoleAssignment,
    Person,
    PersonRelationship,
)
from portal.models import Rider, RiderGuardian, Season, SeasonMembership, Team, UserProfile


class V323RiderFamilyAndIEAStatusTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
        self.admin = User.objects.create_user(username="rider-admin", password="pass12345")
        profile = self.admin.profile
        profile.team = self.team
        profile.role = UserProfile.Role.ADMIN
        profile.save(update_fields=["team", "role"])
        self.client.force_login(self.admin)

        self.rider = Rider.objects.create(
            team=self.team,
            first_name="Jamie",
            last_name="Smith",
            grade=7,
        )
        self.parent_person = Person.objects.create(
            team=self.team,
            first_name="Morgan",
            last_name="Smith",
            email="morgan@example.com",
            phone="555-0100",
        )

    def test_link_existing_person_creates_legacy_and_canonical_parent_relationship(self):
        response = self.client.post(
            reverse("rider_guardian_link", args=[self.rider.pk]),
            {
                "person": self.parent_person.pk,
                "relationship": "Mother",
                "primary_contact": "on",
            },
        )
        self.assertEqual(response.status_code, 302)

        rider_bridge = LegacyPersonLink.objects.get(rider=self.rider)
        parent_bridge = LegacyPersonLink.objects.get(person=self.parent_person)
        legacy_link = RiderGuardian.objects.get(
            rider=self.rider,
            guardian=parent_bridge.guardian,
        )
        self.assertEqual(legacy_link.relationship, "Mother")
        self.assertTrue(legacy_link.primary_contact)

        relationship = PersonRelationship.objects.get(
            from_person=self.parent_person,
            to_person=rider_bridge.person,
            relationship_type=PersonRelationship.RelationshipType.PARENT_GUARDIAN,
        )
        self.assertEqual(relationship.label, "Mother")
        self.assertTrue(relationship.primary_contact)
        self.assertTrue(relationship.active)
        self.assertTrue(
            OrganizationRoleAssignment.objects.filter(
                team=self.team,
                person=self.parent_person,
                role=OrganizationRoleAssignment.Role.PARENT_GUARDIAN,
                active=True,
            ).exists()
        )

    def test_unlink_ends_canonical_relationship_but_keeps_people_records(self):
        self.client.post(
            reverse("rider_guardian_link", args=[self.rider.pk]),
            {"person": self.parent_person.pk, "relationship": "Guardian"},
        )
        link = RiderGuardian.objects.get(rider=self.rider)
        rider_person = LegacyPersonLink.objects.get(rider=self.rider).person

        response = self.client.post(
            reverse("rider_guardian_unlink", args=[self.rider.pk, link.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Person.objects.filter(pk=self.parent_person.pk).exists())
        relationship = PersonRelationship.objects.get(
            from_person=self.parent_person,
            to_person=rider_person,
            relationship_type=PersonRelationship.RelationshipType.PARENT_GUARDIAN,
        )
        self.assertFalse(relationship.active)
        self.assertIsNotNone(relationship.end_date)

    def test_rider_card_uses_active_season_not_historical_membership(self):
        old_season = Season.objects.create(
            team=self.team,
            name="2025-2026",
            start_date=date(2025, 8, 1),
            end_date=date(2026, 6, 30),
            is_active=False,
        )
        active_season = Season.objects.create(
            team=self.team,
            name="2026-2027",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 6, 30),
            is_active=True,
        )
        SeasonMembership.objects.create(
            rider=self.rider,
            season=old_season,
            team_level=SeasonMembership.TeamLevel.FUTURES,
        )

        response = self.client.get(reverse("rider_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "RIDER · NOT ON CURRENT IEA TEAM")
        self.assertNotContains(response, "IEA TEAM · CURRENT")

        SeasonMembership.objects.create(
            rider=self.rider,
            season=active_season,
            team_level=SeasonMembership.TeamLevel.FUTURES,
        )
        response = self.client.get(reverse("rider_list"))
        self.assertContains(response, "IEA TEAM · CURRENT")
        self.assertContains(response, "Futures Team")
