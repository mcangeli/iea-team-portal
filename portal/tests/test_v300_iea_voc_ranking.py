from datetime import date

from django.test import TestCase

from portal.iea_voc import voc_candidates
from portal.models import (
    Rider,
    Season,
    SeasonClass,
    SeasonMembership,
    Show,
    ShowClass,
    ShowEntry,
    ShowResult,
    Team,
)
from portal.model_modules.competition_iea import IEAClassCatalogEntry


class IEAVOCRankingTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="VOC Ranking Team", discipline="hunt_seat")
        self.season = Season.objects.create(
            team=self.team,
            name="2026-2027",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 4, 30),
            is_active=True,
        )
        h1_catalog = IEAClassCatalogEntry.objects.get(rulebook_season="2026-2027", class_code="H1")
        h2_catalog = IEAClassCatalogEntry.objects.get(rulebook_season="2026-2027", class_code="H2")
        self.h1 = SeasonClass.objects.create(
            season=self.season, name=h1_catalog.official_name, team_level="upper",
            discipline="hunt_seat", class_code="H1", catalog_entry=h1_catalog,
        )
        self.h2 = SeasonClass.objects.create(
            season=self.season, name=h2_catalog.official_name, team_level="upper",
            discipline="hunt_seat", class_code="H2", catalog_entry=h2_catalog,
        )
        self.show = Show.objects.create(
            team=self.team, season=self.season, name="Ranking Show",
            show_date=date(2026, 11, 1), competition_level="regular",
        )
        self.h1_show = ShowClass.objects.create(show=self.show, season_class=self.h1, name=self.h1.name, class_number="H1")
        self.h2_show = ShowClass.objects.create(show=self.show, season_class=self.h2, name=self.h2.name, class_number="H2")

    def _add(self, idx, h1_place, h2_place, h1_points, h2_points):
        rider = Rider.objects.create(
            team=self.team, first_name=f"R{idx}", last_name="VOC", grade=12, active=True
        )
        membership = SeasonMembership.objects.create(rider=rider, season=self.season, team_level="upper")
        membership.classes.set([self.h1, self.h2])
        h1_entry = ShowEntry.objects.create(show_class=self.h1_show, rider=rider)
        h2_entry = ShowEntry.objects.create(show_class=self.h2_show, rider=rider)
        ShowResult.objects.create(entry=h1_entry, place=h1_place, manual_points=True, points=h1_points)
        ShowResult.objects.create(entry=h2_entry, place=h2_place, manual_points=True, points=h2_points)
        return rider

    def test_ranking_is_combined_points_then_h1_place(self):
        second = self._add(1, 2, 1, 7, 7)
        first = self._add(2, 1, 2, 7, 7)
        rows = voc_candidates(self.show)
        self.assertEqual([row.rider_id for row in rows], [first.pk, second.pk])

    def test_unresolved_tie_at_tenth_is_retained_and_flagged(self):
        riders = []
        for idx in range(9):
            riders.append(self._add(idx, 1, 1, 20 - idx, 10))
        tenth = self._add(10, 2, 2, 5, 5)
        tied = self._add(11, 2, 3, 5, 5)
        rows = voc_candidates(self.show)
        ids = [row.rider_id for row in rows]
        self.assertIn(tenth.pk, ids)
        self.assertIn(tied.pk, ids)
        self.assertEqual(len(rows), 11)
        self.assertTrue(rows[-1].cutoff_tie)
