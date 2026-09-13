from io import StringIO
from datetime import date

from django.core.management import call_command
from django.test import TestCase

from portal.iea_catalog_reconciliation import reconcile_season_class
from portal.models import Season, SeasonClass, Team
from portal.model_modules.competition_iea import IEAClassCatalogEntry


class IEAClassReconciliationTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Reconciliation Team", discipline="multi")
        self.season = Season.objects.create(
            team=self.team,
            name="2026-2027",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 6, 30),
            is_active=True,
        )

    def make_class(self, **overrides):
        values = {
            "season": self.season,
            "name": "Legacy H1",
            "team_level": SeasonClass.TeamLevel.UPPER,
            "discipline": "hunt_seat",
            "class_code": "H1",
        }
        values.update(overrides)
        return SeasonClass.objects.create(**values)

    def test_dry_run_finds_exact_match_without_persisting_link(self):
        season_class = self.make_class()
        result = reconcile_season_class(
            season_class,
            rulebook_season="2026-2027",
            apply=False,
        )
        self.assertEqual(result.status, "match")
        self.assertIsNotNone(result.catalog_entry_id)
        season_class.refresh_from_db()
        self.assertIsNone(season_class.catalog_entry_id)

    def test_apply_links_exact_match_without_changing_legacy_fields(self):
        season_class = self.make_class(name="Custom H1 Label", sort_order=77)
        result = reconcile_season_class(
            season_class,
            rulebook_season="2026-2027",
            apply=True,
        )
        self.assertEqual(result.status, "linked")
        season_class.refresh_from_db()
        self.assertIsNotNone(season_class.catalog_entry_id)
        self.assertEqual(season_class.name, "Custom H1 Label")
        self.assertEqual(season_class.sort_order, 77)
        self.assertEqual(season_class.class_code, "H1")

    def test_missing_code_is_never_guessed_from_name(self):
        season_class = self.make_class(
            name="H1 Varsity Open Equitation Over Fences",
            class_code="",
        )
        result = reconcile_season_class(
            season_class,
            rulebook_season="2026-2027",
            apply=True,
        )
        self.assertEqual(result.status, "skipped")
        self.assertEqual(result.reason, "missing_class_code")
        season_class.refresh_from_db()
        self.assertIsNone(season_class.catalog_entry_id)

    def test_wrong_team_level_is_not_linked(self):
        season_class = self.make_class(team_level=SeasonClass.TeamLevel.FUTURES)
        result = reconcile_season_class(
            season_class,
            rulebook_season="2026-2027",
            apply=True,
        )
        self.assertEqual(result.status, "unmatched")
        self.assertEqual(result.reason, "team_level_mismatch")
        season_class.refresh_from_db()
        self.assertIsNone(season_class.catalog_entry_id)

    def test_wrong_rulebook_version_is_not_linked(self):
        season_class = self.make_class()
        result = reconcile_season_class(
            season_class,
            rulebook_season="2027-2028",
            apply=True,
        )
        self.assertEqual(result.status, "unmatched")
        self.assertEqual(result.reason, "no_catalog_match")

    def test_existing_link_is_preserved(self):
        entry = IEAClassCatalogEntry.objects.get(
            rulebook_season="2026-2027",
            discipline="hunt_seat",
            class_code="H1",
        )
        season_class = self.make_class(catalog_entry=entry)
        result = reconcile_season_class(
            season_class,
            rulebook_season="2027-2028",
            apply=True,
        )
        self.assertEqual(result.status, "already_linked")
        self.assertEqual(result.catalog_entry_id, entry.pk)

    def test_management_command_defaults_to_dry_run(self):
        season_class = self.make_class()
        out = StringIO()
        call_command(
            "reconcile_iea_class_catalog",
            "--rulebook-season", "2026-2027",
            "--season-id", str(self.season.pk),
            stdout=out,
        )
        season_class.refresh_from_db()
        self.assertIsNone(season_class.catalog_entry_id)
        self.assertIn("DRY RUN", out.getvalue())
        self.assertIn("match=1", out.getvalue())

    def test_management_command_apply_persists_only_exact_matches(self):
        exact = self.make_class(name="Exact")
        missing = self.make_class(name="Missing", class_code="")
        out = StringIO()
        call_command(
            "reconcile_iea_class_catalog",
            "--rulebook-season", "2026-2027",
            "--season-id", str(self.season.pk),
            "--apply",
            stdout=out,
        )
        exact.refresh_from_db()
        missing.refresh_from_db()
        self.assertIsNotNone(exact.catalog_entry_id)
        self.assertIsNone(missing.catalog_entry_id)
        self.assertIn("APPLY", out.getvalue())
