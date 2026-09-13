from datetime import date

from django.test import TestCase

from portal.forms import ShowClassForm
from portal.iea_catalog_season_setup import configure_iea_season_catalog
from portal.models import Season, SeasonClass, Show, ShowClass, Team


class IEAShowClassSetupTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Show Catalog Team", discipline="hunt_seat")
        self.season = Season.objects.create(
            team=self.team,
            name="2026-2027",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 7, 31),
            is_active=True,
        )
        configure_iea_season_catalog(
            season=self.season,
            rulebook_season="2026-2027",
            disciplines=["hunt_seat"],
        )
        self.show = Show.objects.create(
            team=self.team,
            season=self.season,
            name="Catalog Show",
            show_date=date(2026, 10, 1),
        )
        self.h1 = self.season.season_classes.get(class_code="H1")
        self.manual = SeasonClass.objects.create(
            season=self.season,
            name="Special Demonstration Class",
            team_level=SeasonClass.TeamLevel.BOTH,
            discipline="other",
            sort_order=500,
            active=True,
            class_code="SP1",
        )

    def _payload(self, season_class, **extra):
        payload = {
            "season_class": str(season_class.pk),
            "class_number": season_class.class_code,
            "sort_order": "1",
            "prize_list_time": "",
            "estimated_time": "",
            "schedule_note": "",
        }
        payload.update(extra)
        return payload

    def test_official_catalog_class_is_normal_valid_choice(self):
        form = ShowClassForm(self._payload(self.h1), show=self.show)
        self.assertTrue(form.is_valid(), form.errors)
        obj = form.save(commit=False)
        obj.show = self.show
        obj.save()
        self.assertEqual(obj.season_class_id, self.h1.pk)
        self.assertEqual(obj.class_number, "H1")
        self.assertEqual(obj.name, self.h1.name)

    def test_manual_class_requires_explicit_exception_acknowledgement(self):
        form = ShowClassForm(self._payload(self.manual), show=self.show)
        self.assertFalse(form.is_valid())
        self.assertIn("use_manual_special_class", form.errors)

    def test_manual_class_is_allowed_when_exception_is_explicit(self):
        form = ShowClassForm(
            self._payload(self.manual, use_manual_special_class="on"),
            show=self.show,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_choice_labels_distinguish_official_and_manual_classes(self):
        form = ShowClassForm(show=self.show)
        labels = [label for value, label in form.fields["season_class"].choices if value]
        self.assertTrue(any(label.startswith("Official IEA · H1 ·") for label in labels))
        self.assertTrue(any(label.startswith("Manual / special case · SP1 ·") for label in labels))

    def test_already_used_season_class_is_not_offered_twice(self):
        ShowClass.objects.create(
            show=self.show,
            season_class=self.h1,
            name=self.h1.name,
            discipline=self.h1.discipline,
            class_number="H1",
        )
        form = ShowClassForm(show=self.show)
        offered_ids = set(form.fields["season_class"].queryset.values_list("pk", flat=True))
        self.assertNotIn(self.h1.pk, offered_ids)

    def test_unconfigured_legacy_season_keeps_manual_behavior(self):
        legacy_season = Season.objects.create(
            team=self.team,
            name="2025-2026",
            start_date=date(2025, 8, 1),
            end_date=date(2026, 7, 31),
            is_active=False,
        )
        legacy_class = SeasonClass.objects.create(
            season=legacy_season,
            name="Legacy Class",
            team_level=SeasonClass.TeamLevel.UPPER,
            discipline="hunt_seat",
            active=True,
            class_code="LX",
        )
        legacy_show = Show.objects.create(
            team=self.team,
            season=legacy_season,
            name="Legacy Show",
            show_date=date(2026, 4, 1),
        )
        form = ShowClassForm(self._payload(legacy_class), show=legacy_show)
        self.assertTrue(form.is_valid(), form.errors)
