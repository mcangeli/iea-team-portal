from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from portal.model_modules.public_site import PublicShowPublication, PublicSiteProfile
from portal.models import Season, Show, Team
from portal.view_modules.public_site import _public_show_groups


class PublicLiveBoardUrlTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
        self.season = Season.objects.create(
            team=self.team,
            name="2026-2027",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 6, 30),
            is_active=True,
        )
        self.site = PublicSiteProfile.objects.create(
            team=self.team,
            slug="blue-skies-riding-academy",
            enabled=True,
        )
        self.show = Show.objects.create(
            team=self.team,
            season=self.season,
            name="Autumn Invitational",
            show_date=date(2026, 10, 10),
            status=Show.Status.IN_PROGRESS,
        )
        self.publication = PublicShowPublication.objects.create(
            show=self.show,
            slug="autumn-invitational-live",
            is_published=True,
            publish_live_status=True,
        )

    def test_live_url_redirects_to_active_public_show(self):
        response = self.client.get(reverse("public_live_board", args=[self.site.slug]))
        self.assertRedirects(
            response,
            reverse("public_show_detail", args=[self.site.slug, self.publication.slug]),
            fetch_redirect_response=False,
        )

    def test_live_url_falls_back_to_schedule_when_nothing_is_live(self):
        self.show.status = Show.Status.ENTERED
        self.show.save(update_fields=["status"])

        response = self.client.get(reverse("public_live_board", args=[self.site.slug]))
        self.assertRedirects(
            response,
            reverse("public_schedule", args=[self.site.slug]),
            fetch_redirect_response=False,
        )

    def test_unpublished_live_show_is_not_exposed_by_live_url(self):
        self.publication.is_published = False
        self.publication.save(update_fields=["is_published"])

        response = self.client.get(reverse("public_live_board", args=[self.site.slug]))
        self.assertRedirects(
            response,
            reverse("public_schedule", args=[self.site.slug]),
            fetch_redirect_response=False,
        )

    def test_public_navigation_exposes_live_link(self):
        response = self.client.get(reverse("public_site_home", args=[self.site.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("public_live_board", args=[self.site.slug]))
        self.assertContains(response, ">Live<")

    def test_active_past_dated_show_is_not_duplicated_in_past_group(self):
        self.show.show_date = timezone.localdate() - timedelta(days=1)
        self.show.save(update_fields=["show_date"])

        active, upcoming, past = _public_show_groups(self.site)

        self.assertEqual([item["slug"] for item in active], [self.publication.slug])
        self.assertNotIn(self.publication.slug, [item["slug"] for item in upcoming])
        self.assertNotIn(self.publication.slug, [item["slug"] for item in past])
