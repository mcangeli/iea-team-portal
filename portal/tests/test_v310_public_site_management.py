from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.public_site import PublicShowPublication, PublicSiteProfile
from portal.models import Season, Show, Team, UserProfile


class PublicSiteManagementTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Northfield Equestrian", short_name="Northfield")
        self.other_team = Team.objects.create(name="Other Team")
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
            venue="Private Venue",
            address="123 Private Lane",
            host_team="Host Team",
            iea_zone="4",
            iea_region="3",
            notes="Never publish this private note",
        )
        self.admin = User.objects.create_user(username="admin", password="testpass")
        UserProfile.objects.update_or_create(
            user=self.admin,
            defaults={"team": self.team, "role": UserProfile.Role.ADMIN},
        )
        self.rider_user = User.objects.create_user(username="rider", password="testpass")
        UserProfile.objects.update_or_create(
            user=self.rider_user,
            defaults={"team": self.team, "role": UserProfile.Role.RIDER},
        )

    def test_manager_page_requires_authenticated_manager(self):
        response = self.client.get(reverse("public_site_manage"))
        self.assertEqual(response.status_code, 302)

        self.client.force_login(self.rider_user)
        response = self.client.get(reverse("public_site_manage"))
        self.assertIn(response.status_code, {403, 404})

        self.client.force_login(self.admin)
        response = self.client.get(reverse("public_site_manage"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Public site")
        self.assertContains(response, "Autumn Invitational")

    def test_public_site_profile_is_created_private_by_default(self):
        self.client.force_login(self.admin)
        self.client.get(reverse("public_site_manage"))
        profile = PublicSiteProfile.objects.get(team=self.team)
        self.assertFalse(profile.enabled)
        self.assertTrue(profile.slug)

    def test_manager_can_enable_site_and_control_public_identity(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("public_site_manage"),
            {
                "enabled": "on",
                "slug": "northfield",
                "display_name": "Northfield Equestrian Team",
                "tagline": "Ride together.",
                "introduction": "Welcome to our public program page.",
                "publish_logo": "",
                "publish_website": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        profile = PublicSiteProfile.objects.get(team=self.team)
        self.assertTrue(profile.enabled)
        self.assertEqual(profile.slug, "northfield")
        self.assertEqual(profile.display_name, "Northfield Equestrian Team")

    def test_show_publication_editor_is_team_scoped_and_defaults_private(self):
        other_season = Season.objects.create(
            team=self.other_team,
            name="2026-2027",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 6, 30),
        )
        other_show = Show.objects.create(
            team=self.other_team,
            season=other_season,
            name="Other Show",
            show_date=date(2026, 11, 1),
        )
        self.client.force_login(self.admin)

        response = self.client.get(reverse("public_show_publication_edit", args=[self.show.pk]))
        self.assertEqual(response.status_code, 200)
        publication = PublicShowPublication.objects.get(show=self.show)
        self.assertFalse(publication.is_published)

        response = self.client.get(reverse("public_show_publication_edit", args=[other_show.pk]))
        self.assertEqual(response.status_code, 404)

    def test_show_publication_saves_only_publication_controls(self):
        self.client.force_login(self.admin)
        self.client.get(reverse("public_show_publication_edit", args=[self.show.pk]))
        publication = PublicShowPublication.objects.get(show=self.show)

        response = self.client.post(
            reverse("public_show_publication_edit", args=[self.show.pk]),
            {
                "is_published": "on",
                "slug": publication.slug,
                "public_summary": "Public show summary",
                "publish_time": "",
                "publish_venue": "on",
                "publish_address": "",
                "publish_host_team": "on",
                "publish_iea_area": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        publication.refresh_from_db()
        self.show.refresh_from_db()

        self.assertTrue(publication.is_published)
        self.assertTrue(publication.publish_venue)
        self.assertFalse(publication.publish_address)
        self.assertEqual(publication.public_summary, "Public show summary")
        self.assertEqual(self.show.address, "123 Private Lane")
        self.assertEqual(self.show.notes, "Never publish this private note")
