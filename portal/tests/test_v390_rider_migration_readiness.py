from django.core.management import call_command
from datetime import date\n\nfrom django.test import TestCase

from portal.model_modules.people import IEAParticipant, LegacyPersonLink, Person
from portal.models import Rider, Season, SeasonMembership, Team
from portal.services.rider_migration_readiness import audit_rider_migration_readiness


class V390RiderMigrationReadinessTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Readiness Farm")
        self.season = Season.objects.create(\n            team=self.team,\n            name="2026-2027",\n            start_date=date(2026, 7, 1),\n            end_date=date(2027, 6, 30),\n        )
        self.person = Person.objects.create(team=self.team, first_name="Ready", last_name="Rider")
        self.rider = Rider.objects.create(
            team=self.team, first_name="Ready", last_name="Rider",
            iea_member_number="IEA-390",
        )
        LegacyPersonLink.objects.create(person=self.person, rider=self.rider)
        self.participant = IEAParticipant.objects.create(
            team=self.team, person=self.person, legacy_rider=self.rider,
            iea_member_number="IEA-390",
        )
        self.membership = SeasonMembership.objects.create(rider=self.rider, season=self.season)

    def test_fully_bridged_membership_is_ready(self):
        report = audit_rider_migration_readiness(team=self.team)
        self.assertTrue(report.ready)
        self.assertEqual(report.season_memberships_ready, 1)
        self.assertEqual(report.season_memberships_blocked, 0)

    def test_missing_person_bridge_is_reported_and_blocks_membership(self):
        LegacyPersonLink.objects.filter(rider=self.rider).delete()
        report = audit_rider_migration_readiness(team=self.team)
        self.assertEqual(report.riders_without_person_bridge, 1)
        self.assertEqual(report.season_memberships_blocked, 1)
        self.assertIn("missing_person_bridge", [issue.code for issue in report.issues])

    def test_missing_iea_participant_is_reported_and_blocks_membership(self):
        self.participant.delete()
        report = audit_rider_migration_readiness(team=self.team)
        self.assertEqual(report.riders_without_iea_participant, 1)
        self.assertEqual(report.season_memberships_blocked, 1)
        self.assertIn("missing_iea_participant", [issue.code for issue in report.issues])

    def test_member_number_mismatch_is_reported_without_mutation(self):
        self.participant.iea_member_number = "PERSON-SIDE"
        self.participant.save(update_fields=["iea_member_number"])
        report = audit_rider_migration_readiness(team=self.team)
        self.rider.refresh_from_db()
        self.participant.refresh_from_db()
        self.assertIn("member_number_mismatch", [issue.code for issue in report.issues])
        self.assertEqual(self.rider.iea_member_number, "IEA-390")
        self.assertEqual(self.participant.iea_member_number, "PERSON-SIDE")

    def test_command_is_read_only(self):
        before = (Person.objects.count(), Rider.objects.count(), IEAParticipant.objects.count())
        call_command("audit_rider_migration_readiness", team_id=self.team.id)
        after = (Person.objects.count(), Rider.objects.count(), IEAParticipant.objects.count())
        self.assertEqual(before, after)
