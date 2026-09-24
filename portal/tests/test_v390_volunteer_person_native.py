from decimal import Decimal

from django.test import TestCase

from portal.model_modules.people import IEAParticipant, Person
from portal.models import Season, SeasonMembership, Team, VolunteerLog
from portal.view_modules.common import _volunteer_progress_rows


class V390VolunteerPersonNativeTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Person Native Volunteers")
        self.season = Season.objects.create(
            team=self.team,
            name="2026-27",
            start_date="2026-08-01",
            end_date="2027-07-31",
            upper_volunteer_hours_required=Decimal("10.00"),
        )
        self.person = Person.objects.create(
            team=self.team,
            first_name="Taylor",
            last_name="Volunteer",
        )
        self.participant = IEAParticipant.objects.create(
            team=self.team,
            person=self.person,
        )
        self.membership = SeasonMembership.objects.create(
            season=self.season,
            iea_participant=self.participant,
            team_level=SeasonMembership.TeamLevel.UPPER,
        )

    def test_volunteer_log_can_credit_person_without_legacy_rider(self):
        log = VolunteerLog(
            season=self.season,
            person=self.person,
            service_date="2026-09-20",
            hours=Decimal("3.50"),
            category=VolunteerLog.Category.TEAM,
            performed_by="Parent Volunteer",
            description="Team event support",
            status=VolunteerLog.Status.APPROVED,
        )
        log.full_clean()
        log.save()

        self.assertIsNone(log.rider_id)
        self.assertEqual(log.participant_identity, self.person)
        self.assertEqual(str(log), "Taylor Volunteer — 3.50 hours")

    def test_volunteer_progress_uses_person_native_credit(self):
        VolunteerLog.objects.create(
            season=self.season,
            person=self.person,
            service_date="2026-09-20",
            hours=Decimal("3.50"),
            description="Approved work",
            status=VolunteerLog.Status.APPROVED,
        )
        VolunteerLog.objects.create(
            season=self.season,
            person=self.person,
            service_date="2026-09-21",
            hours=Decimal("1.50"),
            description="Pending work",
            status=VolunteerLog.Status.PENDING,
        )

        rows = _volunteer_progress_rows(self.season, [self.participant])

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["person"], self.person)
        self.assertEqual(rows[0]["rider"], self.person)
        self.assertEqual(rows[0]["approved"], Decimal("3.50"))
        self.assertEqual(rows[0]["pending"], Decimal("1.50"))
        self.assertEqual(rows[0]["remaining"], Decimal("6.50"))
        self.assertFalse(rows[0]["complete"])
