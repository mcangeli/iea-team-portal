from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from portal.host_show_models import HostShowOperations, ShowManagerAssignment
from portal.models import Season, Show, Team, UserProfile


class V250HostShowLifecycleTests(TestCase):
    def setUp(self):
        today = timezone.localdate()
        self.team = Team.objects.create(name="Host Lifecycle Team")
        self.season = Season.objects.create(
            team=self.team,
            name="Lifecycle Season",
            start_date=today - timedelta(days=120),
            end_date=today + timedelta(days=240),
            is_active=True,
        )
        self.manager = self.make_user("lifecycle-manager", UserProfile.Role.PARENT)
        self.coach = self.make_user("lifecycle-coach", UserProfile.Role.COACH)
        self.parent = self.make_user("lifecycle-parent", UserProfile.Role.PARENT)

        self.past_open = self.make_show(
            "Past Open Hosted Show",
            today - timedelta(days=2),
            Show.Status.ENTERED,
        )
        self.upcoming = self.make_show(
            "Upcoming Hosted Show",
            today + timedelta(days=14),
            Show.Status.PLANNING,
        )
        self.completed = self.make_show(
            "Completed Hosted Show",
            today - timedelta(days=21),
            Show.Status.COMPLETE,
        )
        self.cancelled = self.make_show(
            "Cancelled Hosted Show",
            today + timedelta(days=30),
            Show.Status.CANCELLED,
        )
        for show in [self.past_open, self.upcoming, self.completed, self.cancelled]:
            ShowManagerAssignment.objects.create(show=show, user=self.manager, active=True)
            HostShowOperations.objects.create(show=show, created_by=self.coach, updated_by=self.coach)

    def make_user(self, username, role):
        user = User.objects.create_user(username=username, password="testpass")
        user.profile.team = self.team
        user.profile.role = role
        user.profile.save(update_fields=["team", "role"])
        return user

    def make_show(self, name, show_date, status):
        return Show.objects.create(
            team=self.team,
            season=self.season,
            name=name,
            show_date=show_date,
            status=status,
            financial_role=Show.FinancialRole.HOSTING_ATTENDING,
        )

    def test_status_not_date_controls_active_manager_dashboard(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("dashboard_show_manager"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Past Open Hosted Show")
        self.assertContains(response, "Upcoming Hosted Show")
        self.assertNotContains(response, "Completed Hosted Show")
        self.assertNotContains(response, "Cancelled Hosted Show")
        self.assertContains(response, "Hosted show history available")

    def test_host_show_list_separates_active_and_archived_history(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("host_show_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ACTIVE HOST WORKSPACES")
        self.assertContains(response, "HOSTED SHOW HISTORY")
        self.assertContains(response, "Past Open Hosted Show")
        self.assertContains(response, "Completed Hosted Show")
        self.assertContains(response, "Cancelled Hosted Show")

    def test_completed_show_manager_keeps_review_access_but_loses_operational_editing(self):
        self.client.force_login(self.manager)
        workspace = self.client.get(reverse("host_show_workspace", args=[self.completed.pk]))
        command_center = self.client.get(reverse("host_command_center", args=[self.completed.pk]))
        self.assertEqual(workspace.status_code, 200)
        self.assertEqual(command_center.status_code, 200)
        self.assertContains(command_center, "Historical command center")
        self.assertEqual(self.client.get(reverse("host_show_edit", args=[self.completed.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("host_duty_add", args=[self.completed.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("host_checkpoint_add", args=[self.completed.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("host_family_publication_edit", args=[self.completed.pk])).status_code, 403)

    def test_cancelled_show_manager_is_also_read_only(self):
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get(reverse("host_show_workspace", args=[self.cancelled.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("host_show_edit", args=[self.cancelled.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("host_duty_add", args=[self.cancelled.pk])).status_code, 403)

    def test_coach_retains_correction_access_on_archived_host_show(self):
        self.client.force_login(self.coach)
        self.assertEqual(self.client.get(reverse("host_show_edit", args=[self.completed.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("host_duty_add", args=[self.completed.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("host_family_publication_edit", args=[self.completed.pk])).status_code, 200)

    def test_unassigned_parent_cannot_use_archive_as_backdoor(self):
        self.client.force_login(self.parent)
        self.assertEqual(self.client.get(reverse("host_show_workspace", args=[self.completed.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("host_command_center", args=[self.completed.pk])).status_code, 403)
