from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.people import IEAParticipant, Person, PersonRelationship
from portal.models import Season, SeasonMembership, Show, ShowAvailability, Team, UserProfile


class V390ShowAvailabilityUITests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Availability Person Native")
        self.season = Season.objects.create(
            team=self.team, name="2026-2027", start_date=date(2026, 8, 1),
            end_date=date(2027, 6, 30), is_active=True,
        )
        self.person = Person.objects.create(
            team=self.team, first_name="Avery", last_name="Available"
        )
        self.participant = IEAParticipant.objects.create(
            team=self.team, person=self.person, active=True
        )
        SeasonMembership.objects.create(
            season=self.season, iea_participant=self.participant,
            team_level=SeasonMembership.TeamLevel.UPPER,
        )
        self.show = Show.objects.create(
            team=self.team, season=self.season, name="Availability Show",
            show_date=date(2026, 10, 10),
        )
        self.manager = User.objects.create_user(username="availability-manager", password="test-pass")
        self.manager.profile.team = self.team
        self.manager.profile.role = UserProfile.Role.ADMIN
        self.manager.profile.save(update_fields=["team", "role"])

    def test_manager_availability_page_seeds_person_native_response_without_rider(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("show_availability", args=[self.show.pk]))

        self.assertEqual(response.status_code, 200)
        availability = ShowAvailability.objects.get(
            show=self.show, iea_participant=self.participant
        )
        self.assertIsNone(availability.rider_id)
        self.assertContains(
            response,
            reverse("show_availability_participant_edit", args=[self.show.pk, self.participant.pk]),
        )
        self.assertEqual(availability.participant_identity, self.person)

    def test_parent_can_edit_person_native_availability_without_rider(self):
        parent_user = User.objects.create_user(username="availability-parent", password="test-pass")
        parent_user.profile.team = self.team
        parent_user.profile.role = UserProfile.Role.PARENT
        parent_user.profile.save(update_fields=["team", "role"])
        parent = Person.objects.create(
            team=self.team, user=parent_user, first_name="Parent", last_name="Available"
        )
        PersonRelationship.objects.create(
            from_person=parent, to_person=self.person,
            relationship_type=PersonRelationship.RelationshipType.PARENT_GUARDIAN,
            active=True,
        )
        self.client.force_login(parent_user)

        response = self.client.post(
            reverse("show_availability_participant_edit", args=[self.show.pk, self.participant.pk]),
            {"status": ShowAvailability.Status.AVAILABLE, "notes": "Ready to ride"},
        )

        self.assertEqual(response.status_code, 302)
        availability = ShowAvailability.objects.get(
            show=self.show, iea_participant=self.participant
        )
        self.assertEqual(availability.status, ShowAvailability.Status.AVAILABLE)
        self.assertEqual(availability.notes, "Ready to ride")
        self.assertIsNone(availability.rider_id)


    def test_legacy_rider_availability_url_remains_a_compatibility_adapter(self):
        from portal.model_modules.people import LegacyPersonLink
        from portal.models import Rider

        rider = Rider.objects.create(
            team=self.team, first_name="Legacy", last_name="Available", active=True
        )
        self.participant.legacy_rider = rider
        self.participant.save(update_fields=["legacy_rider"])
        LegacyPersonLink.objects.create(person=self.person, rider=rider)
        self.client.force_login(self.manager)

        response = self.client.post(
            reverse("show_availability_edit", args=[self.show.pk, rider.pk]),
            {"status": ShowAvailability.Status.AVAILABLE, "notes": "Compatibility path"},
        )

        self.assertEqual(response.status_code, 302)
        availability = ShowAvailability.objects.get(
            show=self.show, iea_participant=self.participant
        )
        self.assertEqual(availability.status, ShowAvailability.Status.AVAILABLE)
        self.assertEqual(availability.notes, "Compatibility path")
