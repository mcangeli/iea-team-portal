from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.iea_catalog_season_setup import configure_iea_season_catalog
from portal.models import Season, SeasonClass, Show, ShowClass, Team, UserProfile


class IEAShowClassSetupUITests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Show UI Team", discipline="hunt_seat")
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
            name="UI Show",
            show_date=date(2026, 10, 15),
        )
        self.h1 = self.season.season_classes.get(class_code="H1")
        self.manual = SeasonClass.objects.create(
            season=self.season,
            name="Special Exhibition",
            team_level=SeasonClass.TeamLevel.BOTH,
            discipline="other",
            active=True,
            class_code="SPX",
        )
        self.user = User.objects.create_user(username="show-admin", password="test-pass")
        self.user.profile.team = self.team
        self.user.profile.role = UserProfile.Role.ADMIN
        self.user.profile.save(update_fields=["team", "role"])
        self.client.force_login(self.user)
        self.url = reverse("show_class_create", args=[self.show.pk])

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

    def test_show_class_page_labels_official_and_exception_choices(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Official IEA")
        self.assertContains(response, "Manual / special case")
        self.assertContains(response, "Use a manual / special-case season class")

    def test_official_class_can_be_added_without_exception(self):
        response = self.client.post(self.url, self._payload(self.h1), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            ShowClass.objects.filter(show=self.show, season_class=self.h1).exists()
        )
        self.assertContains(response, "Season class added to this show")

    def test_manual_class_is_rejected_without_explicit_exception(self):
        response = self.client.post(self.url, self._payload(self.manual))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            ShowClass.objects.filter(show=self.show, season_class=self.manual).exists()
        )
        self.assertContains(response, "Confirm the manual/special-case exception")

    def test_manual_class_can_be_added_with_explicit_exception(self):
        response = self.client.post(
            self.url,
            self._payload(self.manual, use_manual_special_class="on"),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            ShowClass.objects.filter(show=self.show, season_class=self.manual).exists()
        )
