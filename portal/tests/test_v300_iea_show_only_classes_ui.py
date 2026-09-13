from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.iea_catalog_season_setup import configure_iea_season_catalog
from portal.models import Season, Show, Team, UserProfile
from portal.model_modules.competition_iea import IEASeasonCatalogConfiguration


class IEAShowOnlyCatalogUITests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Warm-Up UI Team", discipline="hunt_seat")
        self.season = Season.objects.create(
            team=self.team,
            name="2026-2027",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 7, 31),
            is_active=True,
        )
        IEASeasonCatalogConfiguration.objects.create(
            season=self.season,
            rulebook_season="2026-2027",
            disciplines=["hunt_seat"],
        )
        configure_iea_season_catalog(
            season=self.season,
            rulebook_season="2026-2027",
            disciplines=["hunt_seat"],
        )
        self.show = Show.objects.create(
            team=self.team,
            season=self.season,
            name="Warm-Up UI Show",
            show_date=date(2026, 10, 10),
        )
        self.user = User.objects.create_user(username="warmup-admin", password="test-pass")
        self.user.profile.team = self.team
        self.user.profile.role = UserProfile.Role.ADMIN
        self.user.profile.save(update_fields=["team", "role"])
        self.client.force_login(self.user)

    def test_add_class_page_shows_official_show_only_selector(self):
        response = self.client.get(reverse("show_class_create", args=[self.show.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Official show-only IEA class")
        self.assertContains(response, "H7x/H8x")
        self.assertContains(response, "H13x/H14x")
        self.assertNotContains(response, "W7x/W8x")
        self.assertNotContains(response, "D7x/D8x")
