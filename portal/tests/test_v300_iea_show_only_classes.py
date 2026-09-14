from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase

from portal.forms import ShowClassForm
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
)
from portal.model_modules.competition_iea import (
    IEAClassCatalogEntry,
    IEASeasonCatalogConfiguration,
)


class IEAShowOnlyCatalogTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Show Only Catalog Team", discipline="multi")
        self.season = Season.objects.create(
            team=self.team,
            name="2026-2027",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 7, 31),
            is_active=True,
        )
        self.config = IEASeasonCatalogConfiguration.objects.create(
            season=self.season,
            rulebook_season="2026-2027",
            disciplines=["hunt_seat"],
        )
        configure_iea_season_catalog(
            season=self.season,
            rulebook_season="2026-2027",
            disciplines=["hunt_seat"],
        )
        self.show = Show.objects.create(
            team=self.team,
            season=self.season,
            name="Catalog Warm-Up Show",
            show_date=date(2026, 10, 10),
            competition_level=Show.CompetitionLevel.REGULAR,
        )

    def test_catalog_contains_six_verified_show_only_warmups(self):
        warmups = IEAClassCatalogEntry.objects.filter(
            rulebook_season="2026-2027",
            class_family="warm_up",
            season_assignable=False,
            active=True,
        )
        self.assertEqual(warmups.count(), 6)
        self.assertEqual(set(warmups.values_list("discipline", flat=True)), {"hunt_seat", "western", "dressage"})
        self.assertFalse(warmups.filter(individual_points_enabled=True).exists())
        self.assertFalse(warmups.filter(team_points_enabled=True).exists())

    def test_season_generation_does_not_create_warmup_season_classes(self):
        self.assertEqual(self.season.season_classes.count(), 14)
        self.assertFalse(self.season.season_classes.filter(class_code__icontains="x").exists())

    def test_show_setup_offers_only_configured_discipline_show_only_classes(self):
        form = ShowClassForm(show=self.show)
        choices = form.fields["official_show_only_class"].queryset
        self.assertEqual(choices.count(), 3)
        self.assertEqual(
            set(choices.values_list("class_code", flat=True)),
            {"H7x/H8x", "H13x/H14x", "VOC"},
        )
        self.assertEqual(
            set(choices.values_list("discipline", flat=True)),
            {"hunt_seat"},
        )

    def test_show_only_selection_creates_direct_catalog_show_class(self):
        warmup = IEAClassCatalogEntry.objects.get(
            rulebook_season="2026-2027",
            discipline="hunt_seat",
            class_code="H7x/H8x",
        )
        form = ShowClassForm(
            data={
                "official_show_only_class": str(warmup.pk),
                "season_class": "",
                "class_number": "",
                "sort_order": "0",
                "prize_list_time": "",
                "estimated_time": "",
                "schedule_note": "",
            },
            show=self.show,
        )
        self.assertTrue(form.is_valid(), form.errors)
        show_class = form.save(commit=False)
        show_class.show = self.show
        show_class.save()
        self.assertIsNone(show_class.season_class_id)
        self.assertEqual(show_class.catalog_entry_id, warmup.pk)
        self.assertEqual(show_class.class_number, "H7x/H8x")
        self.assertEqual(show_class.name, warmup.official_name)
        self.assertEqual(show_class.team_level, "upper")

    def test_warmup_entry_requires_prerequisite_show_entry(self):
        rider = Rider.objects.create(
            team=self.team,
            first_name="Upper",
            last_name="Rider",
            grade=10,
            active=True,
        )
        membership = SeasonMembership.objects.create(
            rider=rider,
            season=self.season,
            team_level=SeasonMembership.TeamLevel.UPPER,
        )
        h7 = SeasonClass.objects.get(season=self.season, class_code="H7")
        membership.classes.add(h7)
        h7_show_class = ShowClass.objects.create(
            show=self.show,
            season_class=h7,
            name=h7.name,
            discipline=h7.discipline,
            class_number="H7",
        )
        warmup_catalog = IEAClassCatalogEntry.objects.get(
            rulebook_season="2026-2027",
            discipline="hunt_seat",
            class_code="H7x/H8x",
        )
        warmup_show_class = ShowClass.objects.create(
            show=self.show,
            catalog_entry=warmup_catalog,
            name=warmup_catalog.official_name,
            discipline=warmup_catalog.discipline,
            class_number=warmup_catalog.class_code,
        )
        warmup_entry = ShowEntry(
            show_class=warmup_show_class,
            rider=rider,
            status=ShowEntry.Status.PLANNED,
        )
        with self.assertRaises(ValidationError):
            warmup_entry.full_clean()

        ShowEntry.objects.create(
            show_class=h7_show_class,
            rider=rider,
            status=ShowEntry.Status.ENTERED,
        )
        warmup_entry.full_clean()

    def test_warmup_result_never_receives_points(self):
        rider = Rider.objects.create(
            team=self.team,
            first_name="Points",
            last_name="Check",
            grade=10,
            active=True,
        )
        membership = SeasonMembership.objects.create(
            rider=rider,
            season=self.season,
            team_level=SeasonMembership.TeamLevel.UPPER,
        )
        h7 = SeasonClass.objects.get(season=self.season, class_code="H7")
        membership.classes.add(h7)
        h7_show_class = ShowClass.objects.create(
            show=self.show,
            season_class=h7,
            name=h7.name,
            discipline=h7.discipline,
            class_number="H7",
        )
        ShowEntry.objects.create(
            show_class=h7_show_class,
            rider=rider,
            status=ShowEntry.Status.ENTERED,
        )
        warmup_catalog = IEAClassCatalogEntry.objects.get(
            rulebook_season="2026-2027",
            discipline="hunt_seat",
            class_code="H7x/H8x",
        )
        warmup_show_class = ShowClass.objects.create(
            show=self.show,
            catalog_entry=warmup_catalog,
            name=warmup_catalog.official_name,
            discipline=warmup_catalog.discipline,
            class_number=warmup_catalog.class_code,
        )
        warmup_entry = ShowEntry(
            show_class=warmup_show_class,
            rider=rider,
            status=ShowEntry.Status.ENTERED,
        )
        warmup_entry.full_clean()
        warmup_entry.save()
        result = ShowResult.objects.create(entry=warmup_entry, place=1)
        result.refresh_from_db()
        self.assertIsNone(result.points)
        self.assertFalse(result.manual_points)
