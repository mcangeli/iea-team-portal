from datetime import date

from django.test import TestCase

from portal.model_modules.people import IEAParticipant, Person
from portal.model_modules.public_site import PublicShowPublication, PublicSiteProfile
from portal.model_modules.show_day_state import ShowClassLiveState
from portal.models import (
    Season,
    SeasonClass,
    SeasonMembership,
    Show,
    ShowClass,
    ShowEntry,
    ShowResult,
    Team,
)
from portal.publication import public_show_results_payload


class V390PublicShowResultsPersonNativeTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Public Person Native Results", discipline="hunt_seat")
        self.season = Season.objects.create(
            team=self.team,
            name="2026-2027",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 4, 30),
            is_active=True,
        )
        self.season_class = SeasonClass.objects.create(
            season=self.season,
            name="Upper Open",
            team_level=SeasonClass.TeamLevel.UPPER,
            discipline="hunt_seat",
            class_code="H1",
        )
        self.show = Show.objects.create(
            team=self.team,
            season=self.season,
            name="Person Native Results Show",
            show_date=date(2026, 10, 10),
            competition_level=Show.CompetitionLevel.REGULAR,
        )
        self.show_class = ShowClass.objects.create(
            show=self.show,
            season_class=self.season_class,
            name=self.season_class.name,
            class_number="H1",
        )
        self.person = Person.objects.create(
            team=self.team,
            first_name="Alex",
            preferred_name="Lex",
            last_name="Morgan",
        )
        self.participant = IEAParticipant.objects.create(
            team=self.team,
            person=self.person,
            active=True,
        )
        membership = SeasonMembership.objects.create(
            iea_participant=self.participant,
            season=self.season,
            team_level=SeasonMembership.TeamLevel.UPPER,
        )
        membership.classes.add(self.season_class)
        self.entry = ShowEntry.objects.create(
            show_class=self.show_class,
            iea_participant=self.participant,
            status=ShowEntry.Status.ENTERED,
        )
        ShowResult.objects.create(entry=self.entry, place=1)

        self.site = PublicSiteProfile.objects.create(
            team=self.team,
            slug="person-native-results",
            enabled=True,
        )
        self.publication = PublicShowPublication.objects.create(
            show=self.show,
            site=self.site,
            slug="person-native-show",
            is_published=True,
            publish_results=True,
        )

    def test_public_results_use_person_identity_without_legacy_rider(self):
        payload = public_show_results_payload(self.publication)
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["results"][0]["rider_name"], self.person.display_name)
        self.assertIsNone(self.entry.rider_id)
