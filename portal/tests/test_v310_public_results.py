from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from portal.model_modules.public_site import PublicShowPublication, PublicSiteProfile
from portal.models import Rider, Season, SeasonClass, Show, ShowClass, ShowEntry, ShowResult, Team


class PublicResultsTests(TestCase):
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
        self.show = Show.objects.create(
            team=self.team,
            season=self.season,
            name="October Show",
            show_date=date(2026, 10, 10),
            notes="PRIVATE SHOW NOTES",
        )
        self.publication = PublicShowPublication.objects.create(
            show=self.show,
            slug="october-show",
            is_published=True,
        )
        self.season_class = SeasonClass.objects.create(
            season=self.season,
            name="Varsity Open Flat",
            team_level=SeasonClass.TeamLevel.UPPER,
            discipline="hunt_seat",
            class_code="H1",
        )
        self.show_class = ShowClass.objects.create(
            show=self.show,
            season_class=self.season_class,
            class_number="H1",
        )
        self.placed_rider = Rider.objects.create(
            team=self.team,
            first_name="Published",
            last_name="Rider",
            grade=10,
        )
        self.placed_entry = ShowEntry.objects.create(
            show_class=self.show_class,
            rider=self.placed_rider,
            is_point_rider=True,
            entry_type=ShowEntry.EntryType.BOTH,
            notes="PRIVATE ENTRY STRATEGY",
        )
        ShowResult.objects.create(
            entry=self.placed_entry,
            place=1,
            points=Decimal("99.9"),
            manual_points=True,
            horse_name="PRIVATE HORSE NAME",
            notes="PRIVATE RESULT NOTES",
        )
        self.unplaced_rider = Rider.objects.create(
            team=self.team,
            first_name="Unplaced",
            last_name="Rider",
            grade=11,
        )
        ShowEntry.objects.create(
            show_class=self.show_class,
            rider=self.unplaced_rider,
            notes="PRIVATE UNPLACED ENTRY",
        )

    def _detail(self):
        return self.client.get(
            reverse("public_show_detail", args=[self.site.slug, self.publication.slug])
        )

    def test_results_are_private_by_default(self):
        response = self._detail()
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Results")
        self.assertNotContains(response, "Published Rider")

    def test_published_results_expose_only_placed_rider_and_class_fields(self):
        self.publication.publish_results = True
        self.publication.save(update_fields=["publish_results", "updated_at"])

        response = self._detail()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Results")
        self.assertContains(response, "H1")
        self.assertContains(response, "Varsity Open Flat")
        self.assertContains(response, "Published Rider")
        self.assertNotContains(response, "Unplaced Rider")

        self.assertNotContains(response, "PRIVATE ENTRY STRATEGY")
        self.assertNotContains(response, "PRIVATE UNPLACED ENTRY")
        self.assertNotContains(response, "PRIVATE HORSE NAME")
        self.assertNotContains(response, "PRIVATE RESULT NOTES")
        self.assertNotContains(response, "PRIVATE SHOW NOTES")
        self.assertNotContains(response, "99.9")
        self.assertNotContains(response, "points rider")

    def test_results_publication_does_not_publish_schedule_implicitly(self):
        self.publication.publish_results = True
        self.publication.save(update_fields=["publish_results", "updated_at"])

        response = self._detail()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Results")
        self.assertNotContains(response, "Class order")
