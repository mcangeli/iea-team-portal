from datetime import date

from django.test import TestCase

from portal.iea_catalog_season_setup import configure_iea_season_catalog
from portal.models import Season, SeasonClass, Team
from portal.model_modules.competition_iea import IEASeasonCatalogConfiguration


class IEACatalogSeasonSetupTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Catalog Test Team", discipline="hunt_seat")
        self.season = Season.objects.create(
            team=self.team,
            name="2026-2027",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 7, 31),
            is_active=True,
        )

    def test_hunt_seat_catalog_generates_14_linked_season_classes(self):
        result = configure_iea_season_catalog(
            season=self.season,
            rulebook_season="2026-2027",
            disciplines=["hunt_seat"],
        )
        self.assertEqual(result.created, 14)
        self.assertEqual(result.reused, 0)
        self.assertEqual(result.linked_legacy, 0)
        self.assertEqual(result.conflicts, ())
        self.assertEqual(
            SeasonClass.objects.filter(
                season=self.season,
                catalog_entry__isnull=False,
                discipline="hunt_seat",
            ).count(),
            14,
        )
        config = IEASeasonCatalogConfiguration.objects.get(season=self.season)
        self.assertEqual(config.rulebook_season, "2026-2027")
        self.assertEqual(config.disciplines, ["hunt_seat"])

    def test_rerun_is_idempotent_and_reuses_existing_catalog_classes(self):
        configure_iea_season_catalog(
            season=self.season,
            rulebook_season="2026-2027",
            disciplines=["hunt_seat"],
        )
        result = configure_iea_season_catalog(
            season=self.season,
            rulebook_season="2026-2027",
            disciplines=["hunt_seat"],
        )
        self.assertEqual(result.created, 0)
        self.assertEqual(result.reused, 14)
        self.assertEqual(SeasonClass.objects.filter(season=self.season).count(), 14)

    def test_exact_legacy_class_is_linked_without_rewriting_legacy_fields(self):
        legacy = SeasonClass.objects.create(
            season=self.season,
            name="Our local H1 label",
            team_level="upper",
            discipline="hunt_seat",
            sort_order=99,
            active=False,
            class_code="h1",
        )
        legacy.refresh_from_db()
        canonical_code = legacy.class_code

        result = configure_iea_season_catalog(
            season=self.season,
            rulebook_season="2026-2027",
            disciplines=["hunt_seat"],
        )
        legacy.refresh_from_db()
        self.assertEqual(result.linked_legacy, 1)
        self.assertEqual(result.created, 13)
        self.assertIsNotNone(legacy.catalog_entry_id)
        self.assertEqual(legacy.name, "Our local H1 label")
        self.assertEqual(legacy.sort_order, 99)
        self.assertFalse(legacy.active)
        self.assertEqual(legacy.class_code, canonical_code)
        self.assertEqual(legacy.class_code, "H1")

    def test_multiple_disciplines_can_be_configured(self):
        result = configure_iea_season_catalog(
            season=self.season,
            rulebook_season="2026-2027",
            disciplines=["hunt_seat", "dressage"],
        )
        self.assertEqual(result.created, 28)
        self.assertEqual(result.conflicts, ())
        self.assertEqual(
            SeasonClass.objects.filter(season=self.season, discipline="hunt_seat").count(),
            14,
        )
        self.assertEqual(
            SeasonClass.objects.filter(season=self.season, discipline="dressage").count(),
            14,
        )

    def test_reconfiguration_does_not_delete_classes_from_previous_selection(self):
        configure_iea_season_catalog(
            season=self.season,
            rulebook_season="2026-2027",
            disciplines=["hunt_seat", "western"],
        )
        result = configure_iea_season_catalog(
            season=self.season,
            rulebook_season="2026-2027",
            disciplines=["hunt_seat"],
        )
        self.assertEqual(result.created, 0)
        self.assertEqual(result.reused, 14)
        self.assertEqual(SeasonClass.objects.filter(season=self.season).count(), 28)
        self.assertEqual(
            SeasonClass.objects.filter(season=self.season, discipline="western").count(),
            14,
        )
