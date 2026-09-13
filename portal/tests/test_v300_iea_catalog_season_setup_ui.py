from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.models import Season, SeasonClass, Team, UserProfile
from portal.model_modules.competition_iea import IEASeasonCatalogConfiguration


class IEACatalogSeasonSetupUITests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="UI Catalog Team", discipline="hunt_seat")
        self.season = Season.objects.create(
            team=self.team,
            name="2026-2027",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 7, 31),
            is_active=True,
        )
        self.user = User.objects.create_user(username="catalog-admin", password="test-pass")
        self.user.profile.team = self.team
        self.user.profile.role = UserProfile.Role.ADMIN
        self.user.profile.save(update_fields=["team", "role"])
        self.client.force_login(self.user)

    def test_catalog_mode_uses_existing_season_class_create_route(self):
        response = self.client.get(reverse("season_class_create") + "?catalog=1")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "portal/iea_catalog_configuration.html")
        self.assertContains(response, "Official class catalog")
        self.assertContains(response, "Sync official classes")

    def test_manual_class_create_route_remains_available(self):
        response = self.client.get(reverse("season_class_create"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Official class catalog")

    def test_catalog_post_creates_official_classes_and_redirects_to_season_setup(self):
        response = self.client.post(
            reverse("season_class_create") + "?catalog=1",
            {
                "catalog_mode": "1",
                "rulebook_season": "2026-2027",
                "disciplines": ["hunt_seat"],
            },
            follow=True,
        )
        self.assertRedirects(response, reverse("season_setup"))
        self.assertContains(response, "Official IEA classes synchronized")
        self.assertEqual(
            SeasonClass.objects.filter(
                season=self.season,
                discipline="hunt_seat",
                catalog_entry__isnull=False,
            ).count(),
            14,
        )
        config = IEASeasonCatalogConfiguration.objects.get(season=self.season)
        self.assertEqual(config.rulebook_season, "2026-2027")
        self.assertEqual(config.disciplines, ["hunt_seat"])

    def test_second_sync_is_idempotent_and_reports_reuse(self):
        payload = {
            "catalog_mode": "1",
            "rulebook_season": "2026-2027",
            "disciplines": ["hunt_seat"],
        }
        self.client.post(reverse("season_class_create") + "?catalog=1", payload)
        response = self.client.post(
            reverse("season_class_create") + "?catalog=1",
            payload,
            follow=True,
        )
        self.assertContains(response, "14 reused")
        self.assertContains(response, "0 created")
        self.assertEqual(SeasonClass.objects.filter(season=self.season).count(), 14)

    def test_season_setup_identifies_catalog_backed_classes(self):
        self.client.post(
            reverse("season_class_create") + "?catalog=1",
            {
                "catalog_mode": "1",
                "rulebook_season": "2026-2027",
                "disciplines": ["hunt_seat"],
            },
        )
        response = self.client.get(reverse("season_setup"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "IEA CLASS CATALOG")
        self.assertContains(response, "Official IEA catalog")
        self.assertContains(response, "2026-2027")
