from datetime import date, time

from django.test import TestCase
from django.urls import reverse

from portal.model_modules.public_site import PublicShowPublication, PublicSiteProfile
from portal.models import Rider, Season, SeasonClass, Show, ShowClass, ShowEntry, Team


class PublicScheduleTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Northfield Equestrian", short_name="Northfield")
        self.season = Season.objects.create(
            team=self.team,
            name="2026-2027",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 6, 30),
            is_active=True,
        )
        self.site = PublicSiteProfile.objects.create(
            team=self.team,
            slug="northfield",
            display_name="Northfield Equestrian",
            enabled=True,
        )

    def _published_show(self, name, show_date, slug, **publication_fields):
        show = Show.objects.create(
            team=self.team,
            season=self.season,
            name=name,
            show_date=show_date,
            start_time=time(8, 30),
            venue=f"{name} Venue",
            address=f"{name} Private Address",
            notes=f"{name} INTERNAL NOTES",
        )
        defaults = {"is_published": True}
        defaults.update(publication_fields)
        return PublicShowPublication.objects.create(show=show, slug=slug, **defaults)

    def _class_with_private_entry(self, publication):
        season_class = SeasonClass.objects.create(
            season=self.season,
            name="Varsity Open Flat",
            team_level=SeasonClass.TeamLevel.UPPER,
            discipline="hunt_seat",
            sort_order=10,
            class_code="H1",
        )
        show_class = ShowClass.objects.create(
            show=publication.show,
            season_class=season_class,
            class_number="H1",
            sort_order=10,
            prize_list_time=time(9, 15),
            estimated_time=time(9, 30),
            schedule_note="Ring 1 · after schooling",
        )
        rider = Rider.objects.create(
            team=self.team,
            first_name="Private",
            last_name="Rider",
            grade=10,
        )
        ShowEntry.objects.create(
            show_class=show_class,
            rider=rider,
            is_point_rider=True,
            entry_type=ShowEntry.EntryType.BOTH,
            notes="SECRET POINT RIDER STRATEGY",
        )
        return show_class

    def test_schedule_requires_enabled_public_site(self):
        self.site.enabled = False
        self.site.save(update_fields=["enabled", "updated_at"])

        response = self.client.get(reverse("public_schedule", args=[self.site.slug]))
        self.assertEqual(response.status_code, 404)

    def test_home_previews_only_next_three_upcoming_published_shows(self):
        self._published_show("Past Show", date(2026, 8, 15), "past-show")
        self._published_show("October Show", date(2026, 10, 3), "october-show")
        self._published_show("November Show", date(2026, 11, 7), "november-show")
        self._published_show("December Show", date(2026, 12, 5), "december-show")
        self._published_show("January Show", date(2027, 1, 9), "january-show")

        response = self.client.get(reverse("public_site_home", args=[self.site.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "October Show")
        self.assertContains(response, "November Show")
        self.assertContains(response, "December Show")
        self.assertNotContains(response, "January Show")
        self.assertNotContains(response, "Past Show")
        self.assertContains(response, "View full schedule")

    def test_schedule_groups_upcoming_and_past_published_shows(self):
        self._published_show("Older Past", date(2026, 7, 1), "older-past")
        self._published_show("Recent Past", date(2026, 8, 20), "recent-past")
        self._published_show("Upcoming Show", date(2026, 10, 10), "upcoming-show")

        hidden = Show.objects.create(
            team=self.team,
            season=self.season,
            name="Private Unpublished Show",
            show_date=date(2026, 10, 20),
        )
        PublicShowPublication.objects.create(show=hidden, slug="private-unpublished")

        response = self.client.get(reverse("public_schedule", args=[self.site.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Upcoming Show")
        self.assertContains(response, "Recent Past")
        self.assertContains(response, "Older Past")
        self.assertNotContains(response, "Private Unpublished Show")
        self.assertLess(
            response.content.decode().index("Recent Past"),
            response.content.decode().index("Older Past"),
        )

    def test_schedule_cards_respect_field_level_publication_controls(self):
        self._published_show(
            "Allowlisted Show",
            date(2026, 10, 10),
            "allowlisted-show",
            publish_time=True,
            publish_venue=True,
            publish_address=False,
        )

        response = self.client.get(reverse("public_schedule", args=[self.site.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "8:30 AM")
        self.assertContains(response, "Allowlisted Show Venue")
        self.assertNotContains(response, "Allowlisted Show Private Address")
        self.assertNotContains(response, "Allowlisted Show INTERNAL NOTES")

    def test_class_schedule_is_private_by_default(self):
        publication = self._published_show(
            "October Show",
            date(2026, 10, 10),
            "october-show",
        )
        self._class_with_private_entry(publication)

        response = self.client.get(
            reverse("public_show_detail", args=[self.site.slug, publication.slug])
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Varsity Open Flat")
        self.assertNotContains(response, "Ring 1 · after schooling")

    def test_published_class_schedule_exposes_only_allowlisted_schedule_fields(self):
        publication = self._published_show(
            "October Show",
            date(2026, 10, 10),
            "october-show",
            publish_schedule=True,
        )
        self._class_with_private_entry(publication)

        response = self.client.get(
            reverse("public_show_detail", args=[self.site.slug, publication.slug])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Class order")
        self.assertContains(response, "H1")
        self.assertContains(response, "Varsity Open Flat")
        self.assertContains(response, "9:30 AM")
        self.assertContains(response, "Ring 1 · after schooling")
        self.assertNotContains(response, "Private Rider")
        self.assertNotContains(response, "SECRET POINT RIDER STRATEGY")
        self.assertNotContains(response, "points rider")
