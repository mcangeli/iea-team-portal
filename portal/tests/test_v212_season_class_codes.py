from datetime import date

from django.test import TestCase

from portal.models import Season, SeasonClass, Show, ShowClass, Team


class SeasonClassCodeTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Test Team")
        self.season = Season.objects.create(
            team=self.team,
            name="2026-2027",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 6, 30),
            is_active=True,
        )
        self.show = Show.objects.create(
            team=self.team,
            season=self.season,
            name="Test Show",
            show_date=date(2026, 10, 1),
        )

    def test_show_class_inherits_season_class_code(self):
        season_class = SeasonClass.objects.create(
            season=self.season,
            name="Open Over Fences",
            team_level=SeasonClass.TeamLevel.UPPER,
            class_code="H1",
        )
        show_class = ShowClass.objects.create(
            show=self.show,
            season_class=season_class,
            name=season_class.name,
            class_number="",
        )
        self.assertEqual(show_class.class_number, "H1")

    def test_changing_season_class_code_updates_linked_show_classes(self):
        season_class = SeasonClass.objects.create(
            season=self.season,
            name="Open Flat",
            team_level=SeasonClass.TeamLevel.UPPER,
            class_code="H2",
        )
        show_class = ShowClass.objects.create(
            show=self.show,
            season_class=season_class,
            name=season_class.name,
            class_number="H2",
        )

        season_class.class_code = "h2a"
        season_class.save()
        show_class.refresh_from_db()
        season_class.refresh_from_db()

        self.assertEqual(season_class.class_code, "H2A")
        self.assertEqual(show_class.class_number, "H2A")
