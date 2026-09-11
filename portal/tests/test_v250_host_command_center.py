from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from portal.host_show_models import (
    HostShowDutyAssignment,
    HostShowOperations,
    HostShowReadinessCheckpoint,
    ShowManagerAssignment,
)
from portal.models import Season, Show, ShowLeadAssignment, Team, UserProfile, VolunteerLog


class V250HostCommandCenterTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Command Center Team")
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
            show_date=date(2026, 11, 14),
            financial_role=Show.FinancialRole.HOSTING_ATTENDING,
        )
        self.manager = self.make_user("hostmanager", UserProfile.Role.PARENT)
        self.lead = self.make_user("hostlead", UserProfile.Role.PARENT)
        self.parent = self.make_user("otherparent", UserProfile.Role.PARENT)
        ShowManagerAssignment.objects.create(show=self.show, user=self.manager, active=True)
        ShowLeadAssignment.objects.create(show=self.show, user=self.lead, active=True)
        self.operations = HostShowOperations.objects.create(show=self.show, created_by=self.manager, updated_by=self.manager)

    def make_user(self, username, role):
        user = User.objects.create_user(username=username, password="testpass")
        user.profile.team = self.team
        user.profile.role = role
        user.profile.save(update_fields=["team", "role"])
        return user

    def test_show_manager_can_open_command_center(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("host_command_center", args=[self.show.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Show-Day Command Center")
        self.assertContains(response, "Operational staffing only")
        self.assertContains(response, "They do not count toward, satisfy, or change season volunteer-hour requirements.")

    def test_show_lead_can_view_but_not_add_host_duty(self):
        self.client.force_login(self.lead)
        self.assertEqual(self.client.get(reverse("host_command_center", args=[self.show.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("host_duty_add", args=[self.show.pk])).status_code, 403)

    def test_unassigned_parent_cannot_open_command_center(self):
        self.client.force_login(self.parent)
        self.assertEqual(self.client.get(reverse("host_command_center", args=[self.show.pk])).status_code, 403)

    def test_duty_assignment_does_not_create_volunteer_hours(self):
        self.client.force_login(self.manager)
        before = VolunteerLog.objects.count()
        response = self.client.post(
            reverse("host_duty_add", args=[self.show.pk]),
            {
                "area": HostShowDutyAssignment.Area.GATE,
                "title": "Morning in-gate",
                "assigned_user": self.manager.pk,
                "assigned_name": "",
                "location": "Main Ring",
                "status": HostShowDutyAssignment.Status.PLANNED,
                "instructions": "Keep the next three riders staged.",
                "handoff_notes": "",
                "sort_order": 0,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(HostShowDutyAssignment.objects.filter(operations=self.operations).exists())
        self.assertEqual(VolunteerLog.objects.count(), before)

    def test_manager_can_add_and_complete_readiness_checkpoint(self):
        self.client.force_login(self.manager)
        due = timezone.now() + timedelta(days=5)
        response = self.client.post(
            reverse("host_checkpoint_add", args=[self.show.pk]),
            {
                "title": "Confirm radios",
                "due_at": due.strftime("%Y-%m-%dT%H:%M"),
                "owner": self.manager.pk,
                "status": HostShowReadinessCheckpoint.Status.OPEN,
                "notes": "Charge and label all radios.",
                "sort_order": 0,
            },
        )
        self.assertEqual(response.status_code, 302)
        checkpoint = HostShowReadinessCheckpoint.objects.get(operations=self.operations)
        self.assertEqual(checkpoint.status, HostShowReadinessCheckpoint.Status.OPEN)

        response = self.client.post(
            reverse("host_checkpoint_complete", args=[self.show.pk, checkpoint.pk])
        )
        self.assertEqual(response.status_code, 302)
        checkpoint.refresh_from_db()
        self.assertEqual(checkpoint.status, HostShowReadinessCheckpoint.Status.COMPLETE)
        self.assertIsNotNone(checkpoint.completed_at)

    def test_duty_status_tracks_operational_handoff_only(self):
        duty = HostShowDutyAssignment.objects.create(
            operations=self.operations,
            area=HostShowDutyAssignment.Area.RING,
            title="Ring runner",
            assigned_user=self.manager,
        )
        self.client.force_login(self.manager)
        before = VolunteerLog.objects.count()
        response = self.client.post(
            reverse("host_duty_status", args=[self.show.pk, duty.pk]),
            {"status": HostShowDutyAssignment.Status.HANDED_OFF, "handoff_notes": "Relief briefed."},
        )
        self.assertEqual(response.status_code, 302)
        duty.refresh_from_db()
        self.assertEqual(duty.status, HostShowDutyAssignment.Status.HANDED_OFF)
        self.assertEqual(duty.handoff_notes, "Relief briefed.")
        self.assertEqual(duty.relieved_by, self.manager)
        self.assertEqual(VolunteerLog.objects.count(), before)
