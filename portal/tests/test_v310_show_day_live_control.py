from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.models import Season, Show, ShowLeadAssignment, Team, UserProfile


class ShowDayLiveControlTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
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
            status=Show.Status.ENTERED,
        )
        self.admin = self.make_user("live-admin", UserProfile.Role.ADMIN)
        self.coach = self.make_user("live-coach", UserProfile.Role.COACH)
        self.lead = self.make_user("live-lead", UserProfile.Role.PARENT)
        self.parent = self.make_user("live-parent", UserProfile.Role.PARENT)
        ShowLeadAssignment.objects.create(
            show=self.show,
            user=self.lead,
            active=True,
        )

    def make_user(self, username, role, team=None):
        user = User.objects.create_user(username=username, password="testpass")
        user.profile.team = team or self.team
        user.profile.role = role
        user.profile.save(update_fields=["team", "role"])
        return user

    def update_status(self, user, status):
        self.client.force_login(user)
        return self.client.post(
            reverse("show_day_live_status_update", args=[self.show.pk]),
            {"status": status},
        )

    def test_admin_coach_and_assigned_show_lead_can_update_live_status(self):
        for user, status in (
            (self.admin, Show.Status.IN_PROGRESS),
            (self.coach, Show.Status.PAUSED),
            (self.lead, Show.Status.COMPLETE),
        ):
            response = self.update_status(user, status)
            self.assertEqual(response.status_code, 302)
            self.show.refresh_from_db()
            self.assertEqual(self.show.status, status)

    def test_unassigned_parent_cannot_update_live_status(self):
        response = self.update_status(self.parent, Show.Status.IN_PROGRESS)
        self.assertEqual(response.status_code, 403)
        self.show.refresh_from_db()
        self.assertEqual(self.show.status, Show.Status.ENTERED)

    def test_show_day_quick_control_rejects_non_show_day_status(self):
        response = self.update_status(self.coach, Show.Status.REGISTRATION)
        self.assertEqual(response.status_code, 302)
        self.show.refresh_from_db()
        self.assertEqual(self.show.status, Show.Status.ENTERED)

    def test_other_organization_cannot_update_show(self):
        other_team = Team.objects.create(name="Other Program")
        other_user = self.make_user("other-coach", UserProfile.Role.COACH, team=other_team)
        response = self.update_status(other_user, Show.Status.IN_PROGRESS)
        self.assertEqual(response.status_code, 404)
        self.show.refresh_from_db()
        self.assertEqual(self.show.status, Show.Status.ENTERED)

    def test_show_day_dashboard_displays_quick_control_only_to_allowed_roles(self):
        for user in (self.admin, self.coach, self.lead):
            self.client.force_login(user)
            response = self.client.get(reverse("show_day_dashboard", args=[self.show.pk]))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "LIVE SHOW STATUS")
            self.assertContains(response, "Start show")

        self.client.force_login(self.parent)
        response = self.client.get(reverse("show_day_dashboard", args=[self.show.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "LIVE SHOW STATUS")
