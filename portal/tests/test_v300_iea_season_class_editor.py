from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.models import Season, SeasonClass, Team, UserProfile
from portal.model_modules.competition_iea import (
    IEAClassCatalogEntry,
    IEASeasonCatalogConfiguration,
)


class IEASeasonClassEditorTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Season Class Editor Team", discipline="hunt_seat")
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
        self.h1 = IEAClassCatalogEntry.objects.get(
            rulebook_season="2026-2027",
            discipline="hunt_seat",
            class_code="H1",
        )
        self.user = User.objects.create_user(username="season-class-admin", password="test-pass")
        self.user.profile.team = self.team
        self.user.profile.role = UserProfile.Role.ADMIN
        self.user.profile.save(update_fields=["team", "role"])
        self.client.force_login(self.user)

    def test_add_class_page_exposes_official_catalog_selector(self):
        response = self.client.get(reverse("season_class_create"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Official IEA class")
        self.assertContains(response, "H1")
        self.assertContains(response, self.h1.official_name)

    def test_create_from_official_catalog_populates_canonical_fields(self):
        response = self.client.post(
            reverse("season_class_create"),
            {
                "official_catalog_entry": str(self.h1.pk),
                "name": "",
                "team_level": "",
                "discipline": "",
                "sort_order": "0",
                "active": "on",
                "sync_from_catalog": "on",
            },
        )
        self.assertRedirects(response, reverse("season_setup"))
        season_class = SeasonClass.objects.get(season=self.season, catalog_entry=self.h1)
        self.assertEqual(season_class.name, self.h1.official_name)
        self.assertEqual(season_class.class_code, "H1")
        self.assertEqual(season_class.team_level, self.h1.team_level)
        self.assertEqual(season_class.discipline, self.h1.discipline)
        self.assertEqual(season_class.sort_order, self.h1.sort_order)

    def test_edit_manual_class_can_link_and_sync_to_official_catalog(self):
        manual = SeasonClass.objects.create(
            season=self.season,
            name="Old local open fences",
            team_level="upper",
            discipline="hunt_seat",
            sort_order=99,
            active=True,
            class_code="LOCAL1",
        )
        response = self.client.get(reverse("season_class_edit", args=[manual.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Official IEA class")
        self.assertContains(response, "Sync details from official catalog")

        response = self.client.post(
            reverse("season_class_edit", args=[manual.pk]),
            {
                "official_catalog_entry": str(self.h1.pk),
                "sync_from_catalog": "on",
                "name": manual.name,
                "team_level": manual.team_level,
                "discipline": manual.discipline,
                "sort_order": str(manual.sort_order),
                "active": "on",
            },
        )
        self.assertRedirects(response, reverse("season_setup"))
        manual.refresh_from_db()
        self.assertEqual(manual.catalog_entry_id, self.h1.pk)
        self.assertEqual(manual.name, self.h1.official_name)
        self.assertEqual(manual.class_code, "H1")
        self.assertEqual(manual.team_level, self.h1.team_level)
        self.assertEqual(manual.discipline, self.h1.discipline)
        self.assertEqual(manual.sort_order, self.h1.sort_order)

    def test_linked_class_can_be_resynced_after_local_edits(self):
        linked = SeasonClass.objects.create(
            season=self.season,
            name="Locally edited label",
            team_level=self.h1.team_level,
            discipline=self.h1.discipline,
            sort_order=88,
            active=True,
            class_code="H1",
            catalog_entry=self.h1,
        )
        response = self.client.post(
            reverse("season_class_edit", args=[linked.pk]),
            {
                "official_catalog_entry": str(self.h1.pk),
                "sync_from_catalog": "on",
                "name": linked.name,
                "team_level": linked.team_level,
                "discipline": linked.discipline,
                "sort_order": str(linked.sort_order),
                "active": "on",
            },
        )
        self.assertRedirects(response, reverse("season_setup"))
        linked.refresh_from_db()
        self.assertEqual(linked.name, self.h1.official_name)
        self.assertEqual(linked.sort_order, self.h1.sort_order)
        self.assertEqual(linked.class_code, "H1")
