from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.host_show_models import ShowManagerAssignment
from portal.models import Season, Show, Team, UserProfile
from portal.view_modules import dashboards


class V250ShowManagerDashboardNavigationTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Dashboard Navigation Team")
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
            name="Hosted Invitational",
            show_date=date(2026, 11, 7),
            financial_role=Show.FinancialRole.HOSTING_ATTENDING,
        )
        self.manager = self.make_user("manager-nav", UserProfile.Role.PARENT)
        self.parent = self.make_user("parent-nav", UserProfile.Role.PARENT)
        self.admin = self.make_user("admin-nav", UserProfile.Role.ADMIN)
        self.coach = self.make_user("coach-nav", UserProfile.Role.COACH)
        ShowManagerAssignment.objects.create(show=self.show, user=self.manager, active=True)

    def make_user(self, username, role):
        user = User.objects.create_user(username=username, password="testpass")
        user.profile.team = self.team
        user.profile.role = role
        user.profile.save(update_fields=["team", "role"])
        return user

    def workspace_links(self, user):
        return dashboards._workspace_links(user, self.team, self.season)

    def test_assigned_show_manager_gets_show_manager_workspace(self):
        links = self.workspace_links(self.manager)
        labels = [link["label"] for link in links]
        self.assertIn("Team overview", labels)
        self.assertIn("Show Manager", labels)
        self.assertIn(
            reverse("dashboard_show_manager"),
            [link["url"] for link in links],
        )

    def test_admin_gets_show_manager_workspace_for_oversight(self):
        links = self.workspace_links(self.admin)
        self.assertIn("Show Manager", [link["label"] for link in links])

    def test_unassigned_parent_does_not_get_show_manager_workspace(self):
        links = self.workspace_links(self.parent)
        self.assertNotIn("Show Manager", [link["label"] for link in links])

    def test_inactive_assignment_removes_show_manager_workspace_and_route(self):
        assignment = ShowManagerAssignment.objects.get(show=self.show, user=self.manager)
        assignment.active = False
        assignment.save(update_fields=["active"])
        self.assertNotIn("Show Manager", [link["label"] for link in self.workspace_links(self.manager)])
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get(reverse("dashboard_show_manager")).status_code, 403)

    def test_coach_show_manager_keeps_both_workspaces(self):
        ShowManagerAssignment.objects.create(show=self.show, user=self.coach, active=True)
        labels = [link["label"] for link in self.workspace_links(self.coach)]
        self.assertIn("Coach", labels)
        self.assertIn("Show Manager", labels)

    def test_show_manager_dashboard_route_opens_for_assigned_manager(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("dashboard_show_manager"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hosted Invitational")
        self.assertContains(response, "Team overview")
        self.assertContains(response, "Show Manager")
        self.assertContains(response, "Publish Family Show Info")

    def test_show_manager_dashboard_selector_is_available_to_admin(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("dashboard_show_manager"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Team overview")
        self.assertContains(response, "Coach")
        self.assertContains(response, "Show Manager")
