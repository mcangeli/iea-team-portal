from datetime import date, time

from django.test import TestCase
from django.urls import reverse

from portal.model_modules.public_site import PublicShowPublication, PublicSiteProfile
from portal.models import Season, Show, Team


class PublicPublicationFoundationTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(
            name="Example Equestrian Team",
            short_name="EET",
            discipline="hunt_seat",
            website="https://private-team.example.com",
        )
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
            name="Autumn Invitational",
            show_date=date(2026, 10, 10),
            start_time=time(8, 30),
            venue="Private Venue Name",
            address="123 Private Barn Road",
            host_team="Private Host Team",
            iea_zone="4",
            iea_region="3",
            notes="INTERNAL SHOW NOTES MUST NEVER APPEAR",
        )
        self.site = PublicSiteProfile.objects.create(
            team=self.team,
            slug="example-equestrian",
            display_name="Example Equestrian",
            tagline="Ride together.",
            introduction="Welcome to our public competition page.",
        )
        self.publication = PublicShowPublication.objects.create(
            show=self.show,
            slug="autumn-invitational",
            public_summary="Public show summary.",
        )

    def test_public_site_defaults_to_private(self):
        response = self.client.get(reverse("public_site_home", args=[self.site.slug]))
        self.assertEqual(response.status_code, 404)

    def test_enabled_site_is_anonymous_but_unpublished_show_is_hidden(self):
        self.site.enabled = True
        self.site.save(update_fields=["enabled", "updated_at"])

        response = self.client.get(reverse("public_site_home", args=[self.site.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Example Equestrian")
        self.assertNotContains(response, "Autumn Invitational")
        self.assertNotContains(response, self.team.website)

        show_response = self.client.get(
            reverse("public_show_detail", args=[self.site.slug, self.publication.slug])
        )
        self.assertEqual(show_response.status_code, 404)

    def test_published_show_exposes_only_allowlisted_fields(self):
        self.site.enabled = True
        self.site.save(update_fields=["enabled", "updated_at"])
        self.publication.is_published = True
        self.publication.save(update_fields=["is_published", "updated_at"])

        response = self.client.get(
            reverse("public_show_detail", args=[self.site.slug, self.publication.slug])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Autumn Invitational")
        self.assertContains(response, "Public show summary.")
        self.assertNotContains(response, "Private Venue Name")
        self.assertNotContains(response, "123 Private Barn Road")
        self.assertNotContains(response, "Private Host Team")
        self.assertNotContains(response, "Zone 4")
        self.assertNotContains(response, "Region 3")
        self.assertNotContains(response, "INTERNAL SHOW NOTES MUST NEVER APPEAR")

    def test_field_toggles_publish_only_requested_show_details(self):
        self.site.enabled = True
        self.site.publish_website = True
        self.site.save(update_fields=["enabled", "publish_website", "updated_at"])
        self.publication.is_published = True
        self.publication.publish_time = True
        self.publication.publish_venue = True
        self.publication.publish_iea_area = True
        self.publication.save(
            update_fields=[
                "is_published",
                "publish_time",
                "publish_venue",
                "publish_iea_area",
                "updated_at",
            ]
        )

        home = self.client.get(reverse("public_site_home", args=[self.site.slug]))
        self.assertEqual(home.status_code, 200)
        self.assertContains(home, "Autumn Invitational")
        self.assertContains(home, "Private Venue Name")
        self.assertContains(home, self.team.website)

        detail = self.client.get(
            reverse("public_show_detail", args=[self.site.slug, self.publication.slug])
        )
        self.assertContains(detail, "8:30 AM")
        self.assertContains(detail, "Private Venue Name")
        self.assertContains(detail, "Zone 4")
        self.assertContains(detail, "Region 3")
        self.assertNotContains(detail, "123 Private Barn Road")
        self.assertNotContains(detail, "Private Host Team")
        self.assertNotContains(detail, "INTERNAL SHOW NOTES MUST NEVER APPEAR")

    def test_show_from_another_team_cannot_be_reached_through_site_slug(self):
        other_team = Team.objects.create(name="Other Team", discipline="hunt_seat")
        other_season = Season.objects.create(
            team=other_team,
            name="2026-2027",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 6, 30),
        )
        other_show = Show.objects.create(
            team=other_team,
            season=other_season,
            name="Other Team Show",
            show_date=date(2026, 11, 1),
        )
        other_publication = PublicShowPublication.objects.create(
            show=other_show,
            slug="other-team-show",
            is_published=True,
        )
        self.site.enabled = True
        self.site.save(update_fields=["enabled", "updated_at"])

        response = self.client.get(
            reverse("public_show_detail", args=[self.site.slug, other_publication.slug])
        )
        self.assertEqual(response.status_code, 404)
