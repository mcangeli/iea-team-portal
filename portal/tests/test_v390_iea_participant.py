from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from portal.model_modules.people import IEAParticipant, LegacyPersonLink, Person
from portal.models import Rider, Team


class V390IEAParticipantTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
        self.other_team = Team.objects.create(name="Other Barn")
        self.person = Person.objects.create(
            team=self.team,
            first_name="Emma",
            last_name="Rider",
        )

    def test_person_can_have_iea_identity_without_legacy_rider(self):
        participant = IEAParticipant(
            team=self.team,
            person=self.person,
            iea_member_number="IEA-1001",
        )
        participant.full_clean()
        participant.save()

        self.assertEqual(self.person.iea_participant, participant)
        self.assertIsNone(participant.legacy_rider_id)

    def test_iea_identity_does_not_duplicate_person_identity_fields(self):
        participant = IEAParticipant.objects.create(
            team=self.team,
            person=self.person,
            iea_member_number="IEA-1001",
        )

        self.assertFalse(hasattr(participant, "first_name"))
        self.assertFalse(hasattr(participant, "last_name"))
        self.assertFalse(hasattr(participant, "email"))
        self.assertEqual(participant.person.display_name, "Emma Rider")

    def test_iea_member_number_is_durable_not_season_specific(self):
        participant = IEAParticipant.objects.create(
            team=self.team,
            person=self.person,
            iea_member_number="IEA-1001",
        )

        self.assertFalse(hasattr(participant, "season"))
        self.assertFalse(hasattr(participant, "team_level"))
        self.assertFalse(hasattr(participant, "division"))
        self.assertFalse(hasattr(participant, "class_level"))

    def test_iea_participant_rejects_cross_organization_person(self):
        other_person = Person.objects.create(
            team=self.other_team,
            first_name="Other",
            last_name="Person",
        )
        participant = IEAParticipant(
            team=self.team,
            person=other_person,
            iea_member_number="IEA-2001",
        )

        with self.assertRaises(ValidationError):
            participant.full_clean()

    def test_person_has_only_one_iea_participant_identity(self):
        IEAParticipant.objects.create(
            team=self.team,
            person=self.person,
            iea_member_number="IEA-1001",
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                IEAParticipant.objects.create(
                    team=self.team,
                    person=self.person,
                    iea_member_number="IEA-1002",
                )

    def test_nonblank_iea_member_number_is_unique_within_organization(self):
        IEAParticipant.objects.create(
            team=self.team,
            person=self.person,
            iea_member_number="IEA-1001",
        )
        second_person = Person.objects.create(
            team=self.team,
            first_name="Taylor",
            last_name="Rider",
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                IEAParticipant.objects.create(
                    team=self.team,
                    person=second_person,
                    iea_member_number="IEA-1001",
                )

    def test_same_iea_member_number_may_exist_in_different_organizations(self):
        IEAParticipant.objects.create(
            team=self.team,
            person=self.person,
            iea_member_number="IEA-1001",
        )
        other_person = Person.objects.create(
            team=self.other_team,
            first_name="Other",
            last_name="Rider",
        )
        participant = IEAParticipant.objects.create(
            team=self.other_team,
            person=other_person,
            iea_member_number="IEA-1001",
        )

        self.assertIsNotNone(participant.pk)

    def test_blank_member_number_can_be_used_during_onboarding(self):
        second_person = Person.objects.create(
            team=self.team,
            first_name="Taylor",
            last_name="Rider",
        )
        first = IEAParticipant.objects.create(team=self.team, person=self.person)
        second = IEAParticipant.objects.create(team=self.team, person=second_person)

        self.assertEqual(first.iea_member_number, "")
        self.assertEqual(second.iea_member_number, "")

    def test_legacy_rider_bridge_must_remain_in_same_organization(self):
        other_rider = Rider.objects.create(
            team=self.other_team,
            first_name="Legacy",
            last_name="Rider",
        )
        participant = IEAParticipant(
            team=self.team,
            person=self.person,
            legacy_rider=other_rider,
        )

        with self.assertRaises(ValidationError):
            participant.full_clean()

    def test_legacy_rider_bridge_matches_existing_person_bridge(self):
        rider = Rider.objects.create(
            team=self.team,
            first_name="Emma",
            last_name="Rider",
            iea_member_number="IEA-1001",
        )
        other_rider = Rider.objects.create(
            team=self.team,
            first_name="Other",
            last_name="Rider",
        )
        LegacyPersonLink.objects.create(person=self.person, rider=rider)

        participant = IEAParticipant(
            team=self.team,
            person=self.person,
            legacy_rider=other_rider,
        )

        with self.assertRaises(ValidationError):
            participant.full_clean()

    def test_legacy_rider_bridge_accepts_matching_person_bridge(self):
        rider = Rider.objects.create(
            team=self.team,
            first_name="Emma",
            last_name="Rider",
            iea_member_number="IEA-1001",
        )
        LegacyPersonLink.objects.create(person=self.person, rider=rider)
        participant = IEAParticipant(
            team=self.team,
            person=self.person,
            legacy_rider=rider,
            iea_member_number=rider.iea_member_number,
        )

        participant.full_clean()
        participant.save()

        self.assertEqual(participant.legacy_rider, rider)
        self.assertEqual(participant.person, self.person)
