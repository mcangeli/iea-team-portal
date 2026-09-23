from django.core.exceptions import ValidationError
from django.test import TestCase

from portal.model_modules.people import IEAParticipant, LegacyPersonLink, Person
from portal.models import Rider, Team
from portal.people_compat import (
    backfill_iea_participants,
    ensure_iea_participant_for_person,
    ensure_iea_participant_for_rider,
)


class V390IEAParticipantBackfillTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
        self.person = Person.objects.create(
            team=self.team,
            first_name="Emma",
            last_name="Rider",
        )
        self.rider = Rider.objects.create(
            team=self.team,
            first_name="Emma",
            last_name="Rider",
            iea_member_number="IEA-1001",
        )
        LegacyPersonLink.objects.create(person=self.person, rider=self.rider)

    def test_backfill_uses_existing_legacy_person_link(self):
        participant, created = ensure_iea_participant_for_person(self.person)

        self.assertTrue(created)
        self.assertEqual(participant.person, self.person)
        self.assertEqual(participant.legacy_rider, self.rider)
        self.assertEqual(participant.iea_member_number, "IEA-1001")

    def test_backfill_is_idempotent(self):
        first, first_created = ensure_iea_participant_for_person(self.person)
        second, second_created = ensure_iea_participant_for_person(self.person)

        self.assertTrue(first_created)
        self.assertFalse(second_created)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(IEAParticipant.objects.filter(person=self.person).count(), 1)

    def test_existing_person_side_member_number_is_preserved_when_legacy_is_blank(self):
        participant = IEAParticipant.objects.create(
            team=self.team,
            person=self.person,
            iea_member_number="IEA-CANONICAL",
        )
        self.rider.iea_member_number = ""
        self.rider.save(update_fields=["iea_member_number"])

        result, created = ensure_iea_participant_for_person(self.person)

        self.assertFalse(created)
        self.assertEqual(result.pk, participant.pk)
        self.assertEqual(result.iea_member_number, "IEA-CANONICAL")
        self.assertEqual(result.legacy_rider, self.rider)

    def test_blank_person_side_member_number_is_filled_from_legacy(self):
        participant = IEAParticipant.objects.create(
            team=self.team,
            person=self.person,
            legacy_rider=self.rider,
        )

        result, created = ensure_iea_participant_for_person(self.person)

        self.assertFalse(created)
        self.assertEqual(result.pk, participant.pk)
        self.assertEqual(result.iea_member_number, "IEA-1001")

    def test_conflicting_member_numbers_are_not_silently_overwritten(self):
        IEAParticipant.objects.create(
            team=self.team,
            person=self.person,
            legacy_rider=self.rider,
            iea_member_number="IEA-DIFFERENT",
        )

        with self.assertRaises(ValidationError):
            ensure_iea_participant_for_person(self.person)

    def test_person_without_deterministic_rider_bridge_is_rejected(self):
        unlinked = Person.objects.create(
            team=self.team,
            first_name="No",
            last_name="Bridge",
            email="same@example.com",
        )
        Rider.objects.create(
            team=self.team,
            first_name="No",
            last_name="Bridge",
            email="same@example.com",
            iea_member_number="IEA-2002",
        )

        with self.assertRaises(ValidationError):
            ensure_iea_participant_for_person(unlinked)

        self.assertFalse(IEAParticipant.objects.filter(person=unlinked).exists())

    def test_rider_helper_uses_existing_person_bridge(self):
        participant, created = ensure_iea_participant_for_rider(self.rider)

        self.assertTrue(created)
        self.assertEqual(participant.person, self.person)
        self.assertEqual(Person.objects.filter(team=self.team).count(), 1)

    def test_batch_backfill_reports_created_and_is_rerunnable(self):
        summary = backfill_iea_participants(team=self.team)
        rerun = backfill_iea_participants(team=self.team)

        self.assertEqual(summary["created"], 1)
        self.assertEqual(summary["existing"], 0)
        self.assertEqual(summary["conflicts"], [])
        self.assertEqual(rerun["created"], 0)
        self.assertEqual(rerun["existing"], 1)
        self.assertEqual(rerun["conflicts"], [])

    def test_batch_backfill_reports_conflict_without_replacing_data(self):
        participant = IEAParticipant.objects.create(
            team=self.team,
            person=self.person,
            legacy_rider=self.rider,
            iea_member_number="IEA-DIFFERENT",
        )

        summary = backfill_iea_participants(team=self.team)

        participant.refresh_from_db()
        self.assertEqual(summary["created"], 0)
        self.assertEqual(summary["existing"], 0)
        self.assertEqual(len(summary["conflicts"]), 1)
        self.assertEqual(summary["conflicts"][0]["person_id"], self.person.pk)
        self.assertEqual(participant.iea_member_number, "IEA-DIFFERENT")
