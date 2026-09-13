from types import SimpleNamespace

from django.db import IntegrityError, transaction
from django.test import TestCase

from portal.model_modules.competition_iea import IEAClassCatalogEntry
from portal.view_modules.common import _is_non_team_scoring_class


class IEAClassCatalogTests(TestCase):
    def test_verified_2026_2027_catalog_contains_42_season_classes(self):
        catalog = IEAClassCatalogEntry.objects.filter(
            rulebook_season="2026-2027",
            season_assignable=True,
            active=True,
        )
        self.assertEqual(catalog.count(), 42)
        self.assertEqual(catalog.filter(discipline="hunt_seat").count(), 14)
        self.assertEqual(catalog.filter(discipline="western").count(), 14)
        self.assertEqual(catalog.filter(discipline="dressage").count(), 14)

    def test_walk_trot_classes_keep_individual_points_but_disable_team_points(self):
        for class_code in ["H8", "H14", "W8", "W14", "D8", "D14"]:
            entry = IEAClassCatalogEntry.objects.get(
                rulebook_season="2026-2027",
                class_code=class_code,
            )
            self.assertTrue(entry.individual_points_enabled, class_code)
            self.assertFalse(entry.team_points_enabled, class_code)
            self.assertTrue(entry.season_assignable, class_code)

    def test_same_class_code_can_exist_in_a_later_rulebook_version(self):
        current = IEAClassCatalogEntry.objects.get(
            rulebook_season="2026-2027",
            discipline="hunt_seat",
            class_code="H1",
        )
        later = IEAClassCatalogEntry.objects.create(
            rulebook_season="2027-2028",
            discipline=current.discipline,
            class_code=current.class_code,
            official_name=current.official_name,
            team_level=current.team_level,
            ability_level=current.ability_level,
            class_family=current.class_family,
            individual_points_enabled=current.individual_points_enabled,
            team_points_enabled=current.team_points_enabled,
            season_assignable=current.season_assignable,
            sort_order=current.sort_order,
            source_rule=current.source_rule,
        )
        self.assertNotEqual(current.pk, later.pk)

    def test_class_code_is_unique_inside_one_rulebook_discipline(self):
        current = IEAClassCatalogEntry.objects.get(
            rulebook_season="2026-2027",
            discipline="hunt_seat",
            class_code="H1",
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                IEAClassCatalogEntry.objects.create(
                    rulebook_season=current.rulebook_season,
                    discipline=current.discipline,
                    class_code=current.class_code,
                    official_name="Duplicate",
                    team_level=current.team_level,
                )

    def test_legacy_hunt_seat_scoring_exclusion_is_unchanged(self):
        # v3.0 catalog introduction is additive. Existing scoring behavior stays
        # frozen until the catalog-backed scoring refactor is intentionally made.
        for class_code in ["H8", "H14"]:
            show_class = SimpleNamespace(
                class_number=class_code,
                display_name=f"{class_code} Walk/Trot",
                name="Walk/Trot",
            )
            self.assertTrue(_is_non_team_scoring_class(show_class))

        regular = SimpleNamespace(
            class_number="H7",
            display_name="H7 Walk/Trot/Canter",
            name="Walk/Trot/Canter",
        )
        self.assertFalse(_is_non_team_scoring_class(regular))
