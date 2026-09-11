from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from portal.host_show_models import HostShowOperations, HostShowStaffAssignment, ShowManagerAssignment
from portal.models import Season, Show, ShowLeadAssignment, Team, UserProfile


class V250HostShowOperationsTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Host Operations Team")
        self.season = Season.objects.create(
            team=self.team,
            name="2026-2027",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 6, 30),
            is_active=True,
        )
        self.hosted_show = Show.objects.create(
            team=self.team,
            season=self.season,
            name="Home Invitational",
            show_date=date(2026, 11, 7),
            financial_role=Show.FinancialRole.HOSTING_ATTENDING,
        )
        self.away_show = Show.objects.create(
            team=self.team,
            season=self.season,
            name="Away Invitational",
            show_date=date(2026, 12, 5),
            financial_role=Show.FinancialRole.ATTENDING,
        )
        self.coach = self.make_user("coach250", UserProfile.Role.COACH)
        self.manager = self.make_user("manager250", UserProfile.Role.PARENT)
        self.lead = self.make_user("lead250", UserProfile.Role.PARENT)
        self.parent = self.make_user("parent250", UserProfile.Role.PARENT)
        ShowManagerAssignment.objects.create(show=self.hosted_show, user=self.manager, active=True)
        ShowLeadAssignment.objects.create(show=self.hosted_show, user=self.lead, active=True)

    def make_user(self, username, role):
        user = User.objects.create_user(username=username, password="testpass")
        user.profile.team = self.team
        user.profile.role = role
        user.profile.save(update_fields=["team", "role"])
        return user

    def create_complete_operations(self):
        operations = HostShowOperations.objects.create(
            show=self.hosted_show,
            arrival_instructions="Enter through the north gate.",
            check_in_location="Secretary booth",
            trailer_parking="Grass lot B",
            warmup_schooling="Main warm-up opens at 6:30 AM.",
            ring_operations="Gate calls from Ring 1.",
            volunteer_check_in="Hospitality tent",
            emergency_information="EMT at main office.",
            created_by=self.coach,
            updated_by=self.coach,
        )
        for role, name in [
            (HostShowStaffAssignment.Role.SECRETARY, "Secretary"),
            (HostShowStaffAssignment.Role.JUDGE, "Judge"),
            (HostShowStaffAssignment.Role.STEWARD, "Steward"),
            (HostShowStaffAssignment.Role.GATE, "Gate"),
            (HostShowStaffAssignment.Role.ANNOUNCER, "Announcer"),
            (HostShowStaffAssignment.Role.EMS, "EMS"),
        ]:
            HostShowStaffAssignment.objects.create(operations=operations, role=role, name=name)
        return operations

    def test_coach_can_create_host_plan(self):
        self.client.force_login(self.coach)
        response = self.client.post(
            reverse("host_show_edit", args=[self.hosted_show.pk]),
            {
                "arrival_instructions": "Enter through the north gate.",
                "check_in_location": "Secretary booth",
                "trailer_parking": "Grass lot B",
                "warmup_schooling": "Main warm-up opens at 6:30 AM.",
                "ring_operations": "Gate calls from Ring 1.",
                "volunteer_check_in": "Hospitality tent",
                "emergency_information": "EMT at main office.",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(HostShowOperations.objects.filter(show=self.hosted_show).exists())

    def test_show_manager_can_manage_host_plan_and_staff(self):
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get(reverse("host_show_workspace", args=[self.hosted_show.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("host_show_edit", args=[self.hosted_show.pk])).status_code, 200)
        response = self.client.post(
            reverse("host_staff_add", args=[self.hosted_show.pk]),
            {"role": "secretary", "name": "Jamie Secretary", "active": "on", "sort_order": 0},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(HostShowStaffAssignment.objects.filter(operations__show=self.hosted_show, role="secretary").exists())

    def test_show_lead_can_view_but_not_administer_host_plan(self):
        self.client.force_login(self.lead)
        self.assertEqual(self.client.get(reverse("host_show_workspace", args=[self.hosted_show.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("host_show_edit", args=[self.hosted_show.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("host_staff_add", args=[self.hosted_show.pk])).status_code, 403)

    def test_unassigned_parent_cannot_open_host_workspace(self):
        self.client.force_login(self.parent)
        self.assertEqual(self.client.get(reverse("host_show_workspace", args=[self.hosted_show.pk])).status_code, 403)

    def test_readiness_requires_manager_and_core_show_personnel(self):
        operations = self.create_complete_operations()
        self.assertEqual(operations.readiness_percent, 100)
        self.assertTrue(operations.readiness_complete)

    def test_non_hosted_show_rejects_host_operations_and_manager(self):
        operations = HostShowOperations(show=self.away_show)
        with self.assertRaises(ValidationError):
            operations.full_clean()
        assignment = ShowManagerAssignment(show=self.away_show, user=self.manager)
        with self.assertRaises(ValidationError):
            assignment.full_clean()
