from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from portal.iea_catalog_season_setup import configure_iea_season_catalog
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
    UserProfile,
)
from portal.model_modules.competition_iea import (
    IEAClassCatalogEntry,
    IEASeasonCatalogConfiguration,
    individual_points_enabled_for_show_class,
    team_points_enabled_for_show_class,
)


class CatalogScoringPolicyTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Catalog Scoring Team", discipline="multi")
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
            disciplines=["hunt_seat", "western", "dressage"],
        )
        configure_iea_season_catalog(
            season=self.season,
            rulebook_season="2026-2027",
            disciplines=["hunt_seat", "western", "dressage"],
        )
        self.regular = Show.objects.create(
            team=self.team,
            season=self.season,
            name="Regular Catalog Show",
            show_date=date(2026, 10, 1),
            competition_level=Show.CompetitionLevel.REGULAR,
        )
        self.regionals = Show.objects.create(
            team=self.team,
            season=self.season,
            name="Regional Catalog Show",
            show_date=date(2027, 3, 1),
            competition_level=Show.CompetitionLevel.REGIONAL,
        )

    def _rider_for_class(self, season_class, *, first_name="Policy"):
        rider = Rider.objects.create(
            team=self.team,
            first_name=first_name,
            last_name=season_class.class_code,
            grade=10 if season_class.team_level == SeasonClass.TeamLevel.UPPER else 6,
            active=True,
        )
        membership = SeasonMembership.objects.create(
            rider=rider,
            season=self.season,
            team_level=(
                SeasonMembership.TeamLevel.UPPER
                if season_class.team_level == SeasonClass.TeamLevel.UPPER
                else SeasonMembership.TeamLevel.FUTURES
            ),
        )
        membership.classes.add(season_class)
        return rider

    def _show_class(self, show, code):
        season_class = SeasonClass.objects.get(season=self.season, class_code=code)
        return ShowClass.objects.create(
            show=show,
            season_class=season_class,
            name=season_class.name,
            discipline=season_class.discipline,
            class_number=season_class.class_code,
        )

    def test_all_six_beginner_walk_trot_classes_disable_team_points(self):
        expected = {"H8", "H14", "W8", "W14", "D8", "D14"}
        entries = IEAClassCatalogEntry.objects.filter(
            rulebook_season="2026-2027",
            season_assignable=True,
            team_points_enabled=False,
        )
        self.assertEqual(set(entries.values_list("class_code", flat=True)), expected)

    def test_team_scoring_policy_uses_catalog_across_disciplines(self):
        for code in ["H8", "W8", "D8"]:
            show_class = self._show_class(self.regular, code)
            self.assertFalse(team_points_enabled_for_show_class(show_class), code)
            self.assertTrue(individual_points_enabled_for_show_class(show_class), code)

    def test_legacy_unlinked_h8_fallback_is_preserved(self):
        manual = ShowClass.objects.create(
            show=self.regular,
            name="H8 Walk/Trot legacy",
            discipline="hunt_seat",
            class_number="H8",
        )
        self.assertFalse(team_points_enabled_for_show_class(manual))

    def test_catalog_non_team_class_rejects_regular_point_rider(self):
        show_class = self._show_class(self.regular, "W8")
        rider = self._rider_for_class(show_class.season_class, first_name="Western")
        entry = ShowEntry(
            show_class=show_class,
            rider=rider,
            competition_track=ShowEntry.CompetitionTrack.REGULAR,
            entry_type=ShowEntry.EntryType.BOTH,
            is_point_rider=True,
            status=ShowEntry.Status.ENTERED,
        )
        with self.assertRaisesMessage(ValidationError, "does not award team points"):
            entry.full_clean()

    def test_catalog_non_team_class_rejects_finals_team_track(self):
        show_class = self._show_class(self.regionals, "D8")
        rider = self._rider_for_class(show_class.season_class, first_name="Dressage")
        entry = ShowEntry(
            show_class=show_class,
            rider=rider,
            competition_track=ShowEntry.CompetitionTrack.TEAM,
            entry_type=ShowEntry.EntryType.TEAM,
            status=ShowEntry.Status.ENTERED,
        )
        with self.assertRaisesMessage(ValidationError, "individual-only"):
            entry.full_clean()

    def test_point_rider_action_blocks_catalog_non_team_class(self):
        show_class = self._show_class(self.regular, "W14")
        rider = self._rider_for_class(show_class.season_class, first_name="CoachCheck")
        entry = ShowEntry.objects.create(
            show_class=show_class,
            rider=rider,
            competition_track=ShowEntry.CompetitionTrack.REGULAR,
            entry_type=ShowEntry.EntryType.INDIVIDUAL,
            status=ShowEntry.Status.ENTERED,
        )
        user = User.objects.create_user(username="catalog-scoring-admin", password="test-pass")
        user.profile.team = self.team
        user.profile.role = UserProfile.Role.ADMIN
        user.profile.save(update_fields=["team", "role"])
        self.client.force_login(user)

        response = self.client.post(reverse("point_rider_set", args=[entry.pk]))
        self.assertRedirects(response, reverse("show_detail", args=[self.regular.pk]))
        entry.refresh_from_db()
        self.assertFalse(entry.is_point_rider)
        self.assertEqual(entry.entry_type, ShowEntry.EntryType.INDIVIDUAL)

    def test_individual_points_policy_applies_to_season_backed_catalog_class(self):
        catalog = IEAClassCatalogEntry.objects.create(
            rulebook_season="2026-2027",
            discipline=IEAClassCatalogEntry.Discipline.HUNT_SEAT,
            class_code="TEST-NOIND",
            official_name="Test non-scoring individual class",
            team_level=IEAClassCatalogEntry.TeamLevel.UPPER,
            ability_level="open",
            class_family="test",
            individual_points_enabled=False,
            team_points_enabled=True,
            season_assignable=True,
            active=True,
            sort_order=99,
            source_rule="TEST",
        )
        season_class = SeasonClass.objects.create(
            season=self.season,
            name=catalog.official_name,
            team_level=SeasonClass.TeamLevel.UPPER,
            discipline="hunt_seat",
            sort_order=99,
            active=True,
            class_code=catalog.class_code,
            catalog_entry=catalog,
        )
        show_class = ShowClass.objects.create(
            show=self.regular,
            season_class=season_class,
            name=season_class.name,
            discipline=season_class.discipline,
            class_number=season_class.class_code,
        )
        rider = self._rider_for_class(season_class, first_name="NoPoints")
        entry = ShowEntry.objects.create(
            show_class=show_class,
            rider=rider,
            competition_track=ShowEntry.CompetitionTrack.REGULAR,
            entry_type=ShowEntry.EntryType.INDIVIDUAL,
            status=ShowEntry.Status.ENTERED,
        )
        result = ShowResult.objects.create(entry=entry, place=1)
        result.refresh_from_db()
        self.assertIsNone(result.points)
        self.assertFalse(result.manual_points)
