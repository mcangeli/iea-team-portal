from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.models import Season, Show, Team, UserProfile
from portal.model_modules.competition_iea import IEASeasonCatalogConfiguration


class IEAVOCUITests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="VOC UI Team", discipline="hunt_seat")
        self.season = Season.objects.create(
            team=self.team,
            name="2026-2027",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 4, 30),
            is_active=True,
        )
        IEASeasonCatalogConfiguration.objects.create(
            season=self.season,
            rulebook_season="2026-2027",
            disciplines=["hunt_seat"],
        )
        self.show = Show.objects.create(
            team=self.team,
            season=self.season,
            name="VOC UI Show",
            show_date=date(2026, 10, 18),
            competition_level=Show.CompetitionLevel.REGULAR,
        )
        self.user = User.objects.create_user(username="voc-admin", password="test-pass")
        self.user.profile.team = self.team
        self.user.profile.role = UserProfile.Role.ADMIN
        self.user.profile.save(update_fields=["team", "role"])
        self.client.force_login(self.user)

    def test_add_class_page_offers_voc_as_official_show_only_class(self):
        # ShowClass create requires at least one season class to exist; the catalog
        # configuration itself is verified separately by the Phase D/E suites.
        from portal.models import SeasonClass
        SeasonClass.objects.create(
            season=self.season,
            name="Temporary H1",
            team_level="upper",
            discipline="hunt_seat",
            class_code="H1",
            active=True,
        )
        response = self.client.get(reverse("show_class_create", args=[self.show.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Official show-only IEA class")
        self.assertContains(response, "VOC")
        self.assertContains(response, "Varsity Open Championship")
