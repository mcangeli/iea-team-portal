from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase

from portal.model_modules.people import IEAParticipant, LegacyPersonLink, Person
from portal.models import Rider, Season, SeasonMembership, Team


class V390SeasonMembershipIEAParticipantTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Season Link Farm")
        self.season = Season.objects.create(
            team=self.team,
            name="2026-2027",
            start_date=date(2026, 7, 1),
            end_date=date(2027, 6, 30),
        )
        self.person = Person.objects.create(
            team=self.team, first_name="Season", last_name="Rider"
        )
        self.rider = Rider.objects.create(
            team=self.team, first_name="Season", last_name="Rider"
        )
        LegacyPersonLink.objects.create(person=self.person, rider=self.rider)
        self.participant = IEAParticipant.objects.create(
            team=self.team,
            person=self.person,
            legacy_rider=self.rider,
            iea_member_number="SEASON-390",
        )

    def test_membership_accepts_person_native_iea_participant(self):
        membership = SeasonMembership.objects.create(
            rider=self.rider,
            iea_participant=self.participant,
            season=self.season,
        )
        self.assertEqual(membership.iea_participant.person, self.person)
        self.assertEqual(membership.rider, self.rider)

    def test_legacy_membership_remains_valid_during_transition(self):
        membership = SeasonMembership.objects.create(
            rider=self.rider,
            season=self.season,
        )
        self.assertIsNone(membership.iea_participant)

    def test_person_native_identity_is_unique_per_season(self):
        SeasonMembership.objects.create(
            rider=self.rider,
            iea_participant=self.participant,
            season=self.season,
        )
        other_rider = Rider.objects.create(
            team=self.team, first_name="Compatibility", last_name="Rider"
        )
        with self.assertRaises(Exception):
            SeasonMembership.objects.create(
                rider=other_rider,
                iea_participant=self.participant,
                season=self.season,
            )
