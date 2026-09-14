from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.public_site import PublicShowPublication, PublicSiteProfile
from portal.model_modules.show_day_state import SpectatorShowUpdate
from portal.models import Season, Show, ShowLeadAssignment, Team, UserProfile
from portal.publication import public_spectator_updates_payload


class SpectatorShowUpdateTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
        self.site = PublicSiteProfile.objects.create(
            team=self.team,
            slug="blue-skies-riding-academy",
            enabled=True,
            display_name="Blue Skies Riding Academy",
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
            status=Show.Status.IN_PROGRESS,
        )
        self.publication = PublicShowPublication.objects.create(
            show=self.show,
            slug="autumn-invitational-live",
            is_published=True,
            publish_live_status=True,
        )
        self.admin = self.make_user("spectator-admin", UserProfile.Role.ADMIN)
        self.coach = self.make_user("spectator-coach", UserProfile.Role.COACH)
        self.lead = self.make_user("spectator-lead", UserProfile.Role.PARENT)
        self.parent = self.make_user("spectator-parent", UserProfile.Role.PARENT)
        ShowLeadAssignment.objects.create(show=self.show, user=self.lead, active=True)

    def make_user(self, username, role):
        user = User.objects.create_user(username=username, password="testpass")
        user.profile.team = self.team
        user.profile.role = role
        user.profile.save(update_fields=["team", "role"])
        return user

    def test_public_payload_requires_live_publication(self):
        SpectatorShowUpdate.objects.create(
            show=self.show,
            title="Ring 1 holding",
            message="Please remain near the arena.",
            created_by=self.admin,
        )
        self.assertEqual(len(public_spectator_updates_payload(self.publication)), 1)

        self.publication.publish_live_status = False
        self.publication.save(update_fields=["publish_live_status"])
        self.assertEqual(public_spectator_updates_payload(self.publication), [])

    def test_admin_coach_and_show_lead_can_post_but_parent_cannot(self):
        url = reverse("spectator_announcement_add", args=[self.show.pk])
        for index, user in enumerate((self.admin, self.coach, self.lead), start=1):
            self.client.force_login(user)
            response = self.client.post(
                url,
                {"kind": "announcement", "title": f"Public update {index}", "message": "Spectator-safe text."},
            )
            self.assertEqual(response.status_code, 302)

        self.assertEqual(SpectatorShowUpdate.objects.filter(show=self.show).count(), 3)

        self.client.force_login(self.parent)
        response = self.client.post(url, {"title": "Should not publish"})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(SpectatorShowUpdate.objects.filter(title="Should not publish").exists())

    def test_ring_delay_replaces_previous_delay_and_can_clear(self):
        self.client.force_login(self.coach)
        url = reverse("spectator_ring_delay_update", args=[self.show.pk])

        response = self.client.post(url, {"ring": "Ring 2", "minutes": "15"})
        self.assertEqual(response.status_code, 302)
        active = SpectatorShowUpdate.objects.get(show=self.show, kind=SpectatorShowUpdate.Kind.DELAY, active=True)
        self.assertIn("15 minutes", active.title)

        response = self.client.post(url, {"ring": "Ring 2", "minutes": "30"})
        self.assertEqual(response.status_code, 302)
        active_updates = SpectatorShowUpdate.objects.filter(
            show=self.show,
            kind=SpectatorShowUpdate.Kind.DELAY,
            active=True,
        )
        self.assertEqual(active_updates.count(), 1)
        self.assertIn("30 minutes", active_updates.get().title)

        response = self.client.post(url, {"ring": "Ring 2", "minutes": "0"})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(active_updates.exists())

    def test_public_show_page_renders_spectator_notice(self):
        SpectatorShowUpdate.objects.create(
            show=self.show,
            kind=SpectatorShowUpdate.Kind.DELAY,
            ring="Ring 1",
            title="Ring 1 running about 15 minutes behind",
            message="Published show times are estimates.",
            created_by=self.admin,
        )
        response = self.client.get(
            reverse("public_show_detail", args=[self.site.slug, self.publication.slug])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ring 1 running about 15 minutes behind")
        self.assertContains(response, "Published show times are estimates.")
