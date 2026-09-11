from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.models import (
    FamilyCharge,
    Rider,
    Season,
    SeasonClass,
    SeasonMembership,
    Show,
    ShowClass,
    ShowEntry,
    Team,
    UserProfile,
)


class V198Preview5ReadinessTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Test Team")
        self.season = Season.objects.create(
            team=self.team,
            name="2025-26",
            start_date=date(2025, 8, 1),
            end_date=date(2026, 7, 31),
            is_active=True,
            is_closed=False,
        )
        self.admin = User.objects.create_user(username="admin", password="testpass")
        self.admin.profile.team = self.team
        self.admin.profile.role = UserProfile.Role.ADMIN
        self.admin.profile.save(update_fields=["team", "role"])

        self.coach = User.objects.create_user(username="coach", password="testpass")
        self.coach.profile.team = self.team
        self.coach.profile.role = UserProfile.Role.COACH
        self.coach.profile.save(update_fields=["team", "role"])

        self.rider = Rider.objects.create(
            team=self.team, first_name="Emma", last_name="Brown"
        )
        self.membership = SeasonMembership.objects.create(
            rider=self.rider,
            season=self.season,
            team_level=SeasonMembership.TeamLevel.UPPER,
        )

    def test_archive_readiness_admin_only(self):
        self.client.force_login(self.coach)
        response = self.client.get(
            reverse("season_archive_readiness", args=[self.season.pk])
        )
        self.assertEqual(response.status_code, 403)

        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("season_archive_readiness", args=[self.season.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Archive readiness")

    def test_direct_archive_post_without_confirmation_redirects_to_readiness(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("season_close", args=[self.season.pk]))
        self.assertRedirects(
            response,
            reverse("season_archive_readiness", args=[self.season.pk]),
        )
        self.season.refresh_from_db()
        self.assertFalse(self.season.is_closed)

    def test_readiness_surfaces_incomplete_show_resultless_entry_and_classless_rider(self):
        season_class = SeasonClass.objects.create(
            season=self.season,
            name="Varsity Open Flat",
            team_level=SeasonClass.TeamLevel.UPPER,
        )
        show = Show.objects.create(
            team=self.team,
            season=self.season,
            name="Open Show",
            show_date=date(2025, 10, 1),
            status=Show.Status.ENTERED,
        )
        show_class = ShowClass.objects.create(
            show=show,
            season_class=season_class,
            name=season_class.name,
        )
        ShowEntry.objects.create(
            show_class=show_class,
            rider=self.rider,
            status=ShowEntry.Status.ENTERED,
        )

        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("season_archive_readiness", args=[self.season.pk])
        )
        self.assertContains(response, "Incomplete shows")
        self.assertContains(response, "Entries without results")
        self.assertContains(response, "Riders without classes")
        self.assertContains(response, "Open Show")

    def test_archive_with_warnings_is_allowed_after_explicit_confirmation(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("season_close", args=[self.season.pk]),
            {"confirm_archive": "yes"},
        )
        self.assertRedirects(response, reverse("season_review", args=[self.season.pk]))
        self.season.refresh_from_db()
        self.assertTrue(self.season.is_closed)
        self.assertFalse(self.season.is_active)

    def test_season_review_uses_explicit_admin_context(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("season_review", args=[self.season.pk]))
        self.assertContains(
            response,
            reverse("season_archive_readiness", args=[self.season.pk]),
        )
        self.assertNotContains(response, "user.profile.role")
