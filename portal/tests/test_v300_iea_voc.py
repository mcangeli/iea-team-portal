from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from portal.forms import ShowClassForm, ShowEntryForm
from portal.iea_voc import voc_candidates
from portal.tests.v390_compat import bridge_legacy_rider

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
from portal.model_modules.competition_iea import (
    IEAClassCatalogEntry,
    IEASeasonCatalogConfiguration,
)


class IEAVOCWorkflowTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="VOC Test Team", discipline="hunt_seat")
        self.season = Season.objects.create(
            team=self.team,
            name="2026-2027",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 4, 30),
            is_active=True,
        )
        IEASeasonCatalogConfiguration.objects.create(
            season=self.season,
            rulebook_season="2026-2027",
            disciplines=["hunt_seat"],
        )
        self.h1_catalog = IEAClassCatalogEntry.objects.get(
            rulebook_season="2026-2027", discipline="hunt_seat", class_code="H1"
        )
        self.h2_catalog = IEAClassCatalogEntry.objects.get(
            rulebook_season="2026-2027", discipline="hunt_seat", class_code="H2"
        )
        self.voc_catalog = IEAClassCatalogEntry.objects.get(
            rulebook_season="2026-2027", discipline="hunt_seat", class_code="VOC"
        )
        self.h1 = SeasonClass.objects.create(
            season=self.season,
            name=self.h1_catalog.official_name,
            team_level="upper",
            discipline="hunt_seat",
            class_code="H1",
            sort_order=1,
            active=True,
            catalog_entry=self.h1_catalog,
        )
        self.h2 = SeasonClass.objects.create(
            season=self.season,
            name=self.h2_catalog.official_name,
            team_level="upper",
            discipline="hunt_seat",
            class_code="H2",
            sort_order=2,
            active=True,
            catalog_entry=self.h2_catalog,
        )
        self.show = Show.objects.create(
            team=self.team,
            season=self.season,
            name="Regular VOC Show",
            show_date=date(2026, 10, 3),
            competition_level=Show.CompetitionLevel.REGULAR,
        )
        self.h1_show = ShowClass.objects.create(
            show=self.show, season_class=self.h1, name=self.h1.name, class_number="H1"
        )
        self.h2_show = ShowClass.objects.create(
            show=self.show, season_class=self.h2, name=self.h2.name, class_number="H2"
        )
        self.voc_show = ShowClass.objects.create(
            show=self.show,
            catalog_entry=self.voc_catalog,
            name=self.voc_catalog.official_name,
            class_number="VOC",
        )

    def _rider_with_results(self, suffix, h1_place, h2_place):
        rider = Rider.objects.create(
            team=self.team,
            first_name=f"Rider{suffix}",
            last_name="Open",
            grade=11,
            active=True,
        )
        membership = SeasonMembership.objects.create(
            rider=rider, season=self.season, team_level=SeasonMembership.TeamLevel.UPPER
        )
        membership.classes.set([self.h1, self.h2])
        h1_entry = ShowEntry.objects.create(show_class=self.h1_show, rider=rider)
        h2_entry = ShowEntry.objects.create(show_class=self.h2_show, rider=rider)
        ShowResult.objects.create(entry=h1_entry, place=h1_place)
        ShowResult.objects.create(entry=h2_entry, place=h2_place)
        bridge_legacy_rider(rider)
        return rider

    def test_voc_catalog_is_show_only_and_non_scoring(self):
        self.assertFalse(self.voc_catalog.season_assignable)
        self.assertFalse(self.voc_catalog.individual_points_enabled)
        self.assertFalse(self.voc_catalog.team_points_enabled)
        self.assertEqual(self.voc_catalog.team_level, "upper")
        self.assertEqual(self.voc_catalog.source_rule, "H3303.2")

    def test_show_class_form_offers_voc_on_regular_hunt_seat_show(self):
        fresh_show = Show.objects.create(
            team=self.team,
            season=self.season,
            name="Second Regular Show",
            show_date=date(2026, 10, 10),
            competition_level=Show.CompetitionLevel.REGULAR,
        )
        form = ShowClassForm(show=fresh_show)
        self.assertTrue(form.fields["official_show_only_class"].queryset.filter(pk=self.voc_catalog.pk).exists())

    def test_show_class_form_rejects_voc_on_postseason_show(self):
        postseason = Show.objects.create(
            team=self.team,
            season=self.season,
            name="Region Finals",
            show_date=date(2027, 2, 1),
            competition_level=Show.CompetitionLevel.REGIONAL,
        )
        form = ShowClassForm(
            data={
                "official_show_only_class": str(self.voc_catalog.pk),
                "class_number": "",
                "sort_order": "0",
                "prize_list_time": "",
                "estimated_time": "",
                "schedule_note": "",
            },
            show=postseason,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("regular-season", form.errors["official_show_only_class"][0])

    def test_candidates_require_completed_h1_and_h2_results_and_rank_by_points(self):
        lower = self._rider_with_results("Lower", 3, 3)
        higher = self._rider_with_results("Higher", 1, 2)
        rows = voc_candidates(self.show)
        self.assertEqual(
            [row.person_id for row in rows[:2]],
            [higher.person_bridge.person_id, lower.person_bridge.person_id],
        )
        self.assertGreater(rows[0].total_points, rows[1].total_points)

    def test_voc_entry_form_only_offers_current_candidates(self):
        eligible = self._rider_with_results("Eligible", 1, 1)
        ineligible = Rider.objects.create(
            team=self.team, first_name="No", last_name="Results", grade=11, active=True
        )
        SeasonMembership.objects.create(
            rider=ineligible, season=self.season, team_level=SeasonMembership.TeamLevel.UPPER
        )
        form = ShowEntryForm(
            data={"show_class": str(self.voc_show.pk)},
            show=self.show,
            team=self.team,
        )
        participant_ids = set(
            form.fields["iea_participant"].queryset.values_list("pk", flat=True)
        )
        eligible_participant = bridge_legacy_rider(eligible)
        ineligible_participant = bridge_legacy_rider(ineligible)
        self.assertIn(eligible_participant.pk, participant_ids)
        self.assertNotIn(ineligible_participant.pk, participant_ids)

    def test_model_rejects_ineligible_voc_entry(self):
        rider = Rider.objects.create(
            team=self.team, first_name="Not", last_name="Eligible", grade=11, active=True
        )
        SeasonMembership.objects.create(
            rider=rider, season=self.season, team_level=SeasonMembership.TeamLevel.UPPER
        )
        entry = ShowEntry(show_class=self.voc_show, rider=rider)
        with self.assertRaisesMessage(ValidationError, "not currently eligible for VOC"):
            entry.full_clean()

    def test_voc_result_never_awards_points(self):
        rider = self._rider_with_results("VOC", 1, 1)
        entry = ShowEntry(show_class=self.voc_show, rider=rider)
        entry.full_clean()
        entry.save()
        result = ShowResult.objects.create(
            entry=entry,
            place=1,
            manual_points=True,
            points=Decimal("99"),
        )
        result.refresh_from_db()
        self.assertIsNone(result.points)
        self.assertFalse(result.manual_points)
