from datetime import date

from django.db.models.deletion import ProtectedError
from django.test import TestCase

from portal.models import SeasonClass, Season, Team
from portal.model_modules.competition_iea import IEAClassCatalogEntry


class SeasonClassCatalogLinkTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="ArenaLine Staging Team", discipline="hunt_seat")
        self.season = Season.objects.create(
            team=self.team,
            name="2026-2027",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 6, 30),
            is_active=True,
        )

    def test_legacy_season_class_remains_valid_without_catalog_link(self):
        season_class = SeasonClass.objects.create(
            season=self.season,
            name="Legacy Custom Class",
            team_level=SeasonClass.TeamLevel.UPPER,
            discipline="hunt_seat",
            class_code="LEGACY",
        )
        self.assertIsNone(season_class.catalog_entry)

    def test_season_class_can_link_to_verified_catalog_entry(self):
        catalog = IEAClassCatalogEntry.objects.get(
            rulebook_season="2026-2027",
            discipline="hunt_seat",
            class_code="H1",
        )
        season_class = SeasonClass.objects.create(
            season=self.season,
            name=catalog.official_name,
            team_level=catalog.team_level,
            discipline=catalog.discipline,
            class_code=catalog.class_code,
            catalog_entry=catalog,
        )
        season_class.refresh_from_db()
        self.assertEqual(season_class.catalog_entry_id, catalog.pk)
        self.assertEqual(catalog.season_classes.get(), season_class)

    def test_catalog_entry_is_protected_once_used_by_season_class(self):
        catalog = IEAClassCatalogEntry.objects.get(
            rulebook_season="2026-2027",
            discipline="hunt_seat",
            class_code="H2",
        )
        SeasonClass.objects.create(
            season=self.season,
            name=catalog.official_name,
            team_level=catalog.team_level,
            discipline=catalog.discipline,
            class_code=catalog.class_code,
            catalog_entry=catalog,
        )
        with self.assertRaises(ProtectedError):
            catalog.delete()

    def test_link_does_not_rewrite_existing_season_class_values(self):
        catalog = IEAClassCatalogEntry.objects.get(
            rulebook_season="2026-2027",
            discipline="hunt_seat",
            class_code="H3",
        )
        season_class = SeasonClass.objects.create(
            season=self.season,
            name="Organization display name retained",
            team_level=SeasonClass.TeamLevel.UPPER,
            discipline="hunt_seat",
            class_code="H3",
            catalog_entry=catalog,
        )
        self.assertEqual(season_class.name, "Organization display name retained")
        self.assertEqual(season_class.class_code, "H3")
