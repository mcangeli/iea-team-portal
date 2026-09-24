from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.people import IEAParticipant, OrganizationRoleAssignment, Person
from portal.models import Season, SeasonClass, SeasonMembership, Team, UserProfile


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
