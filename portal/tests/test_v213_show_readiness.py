from datetime import date

from django.test import TestCase

from portal.horse_models import Horse, HorseShowAssignment
from portal.models import Rider, Season, SeasonClass, Show, ShowClass, ShowEntry, Team
from portal.show_readiness_models import ShowLeasedHorse
from portal.show_readiness_service import build_show_readiness


class ShowReadinessTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Test Team")
        self.season = Season.objects.create(
            team=self.team,
            name="2026-2027",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 6, 30),
            is_active=True,
            rides_per_contributed_horse=5,
        )
        self.show = Show.objects.create(
            team=self.team,
            season=self.season,
            name="Test Show",
            show_date=date(2026, 10, 1),
        )
        self.season_class = SeasonClass.objects.create(
            season=self.season,
            name="Open Flat",
            team_level=SeasonClass.TeamLevel.UPPER,
            class_code="H2",
        )
        self.show_class = ShowClass.objects.create(
            show=self.show,
            season_class=self.season_class,
            name=self.season_class.name,
            class_number="H2",
        )

    def _add_entries(self, count):
        for idx in range(count):
            rider = Rider.objects.create(
                team=self.team,
                first_name=f"Rider{idx}",
                last_name="Test",
            )
            ShowEntry.objects.create(
                show_class=self.show_class,
                rider=rider,
                status=ShowEntry.Status.ENTERED,
            )

    def _add_registry_horse(self, name="Team Horse", cover_class=True):
        horse = Horse.objects.create(team=self.team, name=name)
        assignment = HorseShowAssignment.objects.create(show=self.show, horse=horse, available=True)
        if cover_class:
            assignment.show_classes.add(self.show_class)
        return assignment

    def test_required_horses_rounds_up(self):
        self._add_entries(6)
        readiness = build_show_readiness(self.show)
        self.assertEqual(readiness["total_rides"], 6)
        self.assertEqual(readiness["required_horses"], 2)

    def test_leased_horses_count_toward_total_and_class_coverage(self):
        self._add_entries(10)
        self._add_registry_horse("Team One")
        leased = ShowLeasedHorse.objects.create(show=self.show, barn_name="Lease One", available=True)
        leased.show_classes.add(self.show_class)

        readiness = build_show_readiness(self.show)
        self.assertEqual(readiness["required_horses"], 2)
        self.assertEqual(readiness["registry_horses"], 1)
        self.assertEqual(readiness["leased_horses"], 1)
        self.assertEqual(readiness["available_horses"], 2)
        self.assertTrue(readiness["count_ready"])
        self.assertTrue(readiness["coverage_ready"])
        self.assertTrue(readiness["ready"])

    def test_count_can_pass_while_class_coverage_fails(self):
        self._add_entries(5)
        self._add_registry_horse(cover_class=False)

        readiness = build_show_readiness(self.show)
        self.assertEqual(readiness["required_horses"], 1)
        self.assertTrue(readiness["count_ready"])
        self.assertFalse(readiness["coverage_ready"])
        self.assertEqual(readiness["uncovered_class_count"], 1)
        self.assertFalse(readiness["ready"])

    def test_scratched_entries_do_not_count_as_rides(self):
        rider = Rider.objects.create(team=self.team, first_name="Scratch", last_name="Rider")
        ShowEntry.objects.create(
            show_class=self.show_class,
            rider=rider,
            status=ShowEntry.Status.SCRATCHED,
        )
        readiness = build_show_readiness(self.show)
        self.assertEqual(readiness["total_rides"], 0)
        self.assertEqual(readiness["required_horses"], 0)
