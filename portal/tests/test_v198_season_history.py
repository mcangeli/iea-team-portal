from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.models import AuditEvent, Rider, Season, SeasonMembership, Team, UserProfile


class V198SeasonHistoryTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Test Team")
        self.season = Season.objects.create(
            team=self.team,
            name="2025-26",
            start_date=date(2025, 8, 1),
            end_date=date(2026, 7, 31),
            is_active=False,
            is_closed=True,
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
            team=self.team,
            first_name="Emma",
            last_name="Brown",
            grade=8,
        )
        SeasonMembership.objects.create(
            rider=self.rider,
            season=self.season,
            team_level=SeasonMembership.TeamLevel.FUTURES,
        )

    def test_manager_can_open_historical_data_workspace(self):
        self.client.force_login(self.coach)
        response = self.client.get(
            reverse("season_history_entry", args=[self.season.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Historical season entry")
        self.assertContains(response, "Emma Brown")

    def test_parent_cannot_open_historical_data_workspace(self):
        parent = User.objects.create_user(username="parent", password="testpass")
        parent.profile.team = self.team
        parent.profile.role = UserProfile.Role.PARENT
        parent.profile.save(update_fields=["team", "role"])
        self.client.force_login(parent)
        response = self.client.get(
            reverse("season_history_entry", args=[self.season.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_reopen_is_audited_and_does_not_activate(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("season_reopen", args=[self.season.pk])
        )
        self.assertRedirects(
            response, reverse("season_review", args=[self.season.pk])
        )
        self.season.refresh_from_db()
        self.assertFalse(self.season.is_closed)
        self.assertFalse(self.season.is_active)
        self.assertTrue(
            AuditEvent.objects.filter(
                season=self.season,
                action=AuditEvent.Action.RESTORED,
                summary__icontains="Reopened archived season",
            ).exists()
        )

    def test_admin_archive_is_audited(self):
        self.season.is_closed = False
        self.season.is_active = True
        self.season.save(update_fields=["is_closed", "is_active"])
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("season_close", args=[self.season.pk]),
            {"confirm_archive": "yes"},
        )
        self.assertRedirects(
            response, reverse("season_review", args=[self.season.pk])
        )
        self.season.refresh_from_db()
        self.assertTrue(self.season.is_closed)
        self.assertFalse(self.season.is_active)
        self.assertTrue(
            AuditEvent.objects.filter(
                season=self.season,
                action=AuditEvent.Action.UPDATED,
                summary__icontains="Archived season",
            ).exists()
        )

    def test_repeated_reopen_does_not_create_extra_audit_event(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("season_reopen", args=[self.season.pk]))
        count = AuditEvent.objects.filter(season=self.season).count()
        self.client.post(reverse("season_reopen", args=[self.season.pk]))
        self.assertEqual(
            AuditEvent.objects.filter(season=self.season).count(),
            count,
        )
