from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.host_show_models import ShowManagerAssignment
from portal.models import Season, Show, ShowLeadAssignment, Team, UserProfile


class V250HostRoleMatrixTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Host Role Matrix Team")
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
            name="Hosted Role Matrix Show",
            show_date=date(2026, 12, 12),
            financial_role=Show.FinancialRole.HOSTING_ATTENDING,
        )
        self.manager_one = self.make_user("manager-one", UserProfile.Role.PARENT)
        self.manager_two = self.make_user("manager-two", UserProfile.Role.PARENT)
        self.lead = self.make_user("show-lead", UserProfile.Role.PARENT)
        self.coach = self.make_user("host-coach", UserProfile.Role.COACH)
        self.admin = self.make_user("host-admin", UserProfile.Role.ADMIN)
        self.parent = self.make_user("host-parent", UserProfile.Role.PARENT)
        self.rider = self.make_user("host-rider", UserProfile.Role.RIDER)
        ShowManagerAssignment.objects.create(show=self.show, user=self.manager_one, active=True)
        ShowManagerAssignment.objects.create(show=self.show, user=self.manager_two, active=True)
        ShowLeadAssignment.objects.create(show=self.show, user=self.lead, active=True)

    def make_user(self, username, role):
        user = User.objects.create_user(username=username, password="testpass")
        user.profile.team = self.team
        user.profile.role = role
        user.profile.save(update_fields=["team", "role"])
        return user

    def get_as(self, user, route_name):
        self.client.force_login(user)
        return self.client.get(reverse(route_name, args=[self.show.pk]))

    def test_multiple_show_managers_can_manage_same_hosted_show(self):
        for user in (self.manager_one, self.manager_two):
            self.assertEqual(self.get_as(user, "host_show_workspace").status_code, 200)
            self.assertEqual(self.get_as(user, "host_show_edit").status_code, 200)
            self.assertEqual(self.get_as(user, "host_command_center").status_code, 200)
            self.assertEqual(self.get_as(user, "host_family_publication_edit").status_code, 200)

    def test_deactivating_one_manager_does_not_affect_other_manager(self):
        assignment = ShowManagerAssignment.objects.get(show=self.show, user=self.manager_one)
        assignment.active = False
        assignment.save(update_fields=["active"])

        self.assertEqual(self.get_as(self.manager_one, "host_show_workspace").status_code, 403)
        self.assertEqual(self.get_as(self.manager_two, "host_show_workspace").status_code, 200)
        self.assertEqual(self.get_as(self.manager_two, "host_show_edit").status_code, 200)

    def test_show_lead_is_view_only_for_host_administration(self):
        self.assertEqual(self.get_as(self.lead, "host_show_workspace").status_code, 200)
        self.assertEqual(self.get_as(self.lead, "host_command_center").status_code, 200)
        self.assertEqual(self.get_as(self.lead, "host_show_edit").status_code, 403)
        self.assertEqual(self.get_as(self.lead, "host_staff_add").status_code, 403)
        self.assertEqual(self.get_as(self.lead, "host_checkpoint_add").status_code, 403)
        self.assertEqual(self.get_as(self.lead, "host_duty_add").status_code, 403)
        self.assertEqual(self.get_as(self.lead, "host_family_publication_edit").status_code, 403)

    def test_user_who_is_both_show_manager_and_show_lead_can_manage(self):
        ShowLeadAssignment.objects.create(show=self.show, user=self.manager_one, active=True)
        self.assertEqual(self.get_as(self.manager_one, "host_show_workspace").status_code, 200)
        self.assertEqual(self.get_as(self.manager_one, "host_show_edit").status_code, 200)
        self.assertEqual(self.get_as(self.manager_one, "host_family_publication_edit").status_code, 200)

    def test_coach_and_admin_can_manage_without_show_manager_assignment(self):
        for user in (self.coach, self.admin):
            self.assertEqual(self.get_as(user, "host_show_workspace").status_code, 200)
            self.assertEqual(self.get_as(user, "host_show_edit").status_code, 200)
            self.assertEqual(self.get_as(user, "host_command_center").status_code, 200)
            self.assertEqual(self.get_as(user, "host_family_publication_edit").status_code, 200)

    def test_unassigned_parent_and_rider_cannot_access_host_operations(self):
        for user in (self.parent, self.rider):
            self.assertEqual(self.get_as(user, "host_show_workspace").status_code, 403)
            self.assertEqual(self.get_as(user, "host_command_center").status_code, 403)
            self.assertEqual(self.get_as(user, "host_show_edit").status_code, 403)
            self.assertEqual(self.get_as(user, "host_family_publication_edit").status_code, 403)
