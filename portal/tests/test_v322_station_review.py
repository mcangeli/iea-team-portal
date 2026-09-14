from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from portal.model_modules.people import Person
from portal.model_modules.station import WorkShiftEntry
from portal.models import AuditEvent, Team, UserProfile


class V322StationReviewTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
        self.other_team = Team.objects.create(name="Other Barn")
        self.admin = User.objects.create_user(username="station-review-admin", password="pass12345")
        profile = self.admin.profile
        profile.team = self.team
        profile.role = UserProfile.Role.ADMIN
        profile.save(update_fields=["team", "role"])
        self.member = User.objects.create_user(username="station-review-member", password="pass12345")
        profile = self.member.profile
        profile.team = self.team
        profile.role = UserProfile.Role.PARENT
        profile.save(update_fields=["team", "role"])
        self.person = Person.objects.create(team=self.team, first_name="Jamie", last_name="Smith")
        self.other_person = Person.objects.create(team=self.other_team, first_name="Taylor", last_name="Jones")
        now = timezone.now().replace(second=0, microsecond=0)
        self.shift = WorkShiftEntry.objects.create(
            team=self.team,
            person=self.person,
            role=WorkShiftEntry.Role.WORKING_STUDENT,
            clock_in=now - timedelta(hours=2),
            clock_out=now,
        )
        self.other_shift = WorkShiftEntry.objects.create(
            team=self.other_team,
            person=self.other_person,
            role=WorkShiftEntry.Role.BARN_STAFF,
            clock_in=now - timedelta(hours=1),
            clock_out=now,
        )

    def test_review_is_manager_only_and_tenant_scoped(self):
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(reverse("station_shift_review")).status_code, 403)
        self.client.force_login(self.admin)
        response = self.client.get(reverse("station_shift_review"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.person.display_name)
        self.assertNotContains(response, self.other_person.display_name)

    def test_manager_can_approve_closed_shift_and_audit_event_is_created(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("station_shift_approve", args=[self.shift.pk]))
        self.assertEqual(response.status_code, 302)
        self.shift.refresh_from_db()
        self.assertEqual(self.shift.approved_by, self.admin)
        self.assertIsNotNone(self.shift.approved_at)
        self.assertTrue(
            AuditEvent.objects.filter(
                team=self.team,
                actor=self.admin,
                action="station_shift_approved",
                entity_type="WorkShiftEntry",
                entity_id=self.shift.pk,
            ).exists()
        )

    def test_open_shift_cannot_be_approved(self):
        open_shift = WorkShiftEntry.objects.create(
            team=self.team,
            person=self.person,
            role=WorkShiftEntry.Role.WORKING_STUDENT,
            clock_in=timezone.now(),
        )
        self.client.force_login(self.admin)
        response = self.client.post(reverse("station_shift_approve", args=[open_shift.pk]))
        self.assertEqual(response.status_code, 302)
        open_shift.refresh_from_db()
        self.assertIsNone(open_shift.approved_at)

    def test_manager_correction_is_tenant_scoped_and_audited(self):
        self.client.force_login(self.admin)
        new_clock_out = self.shift.clock_out + timedelta(minutes=30)
        response = self.client.post(
            reverse("station_shift_edit", args=[self.shift.pk]),
            {
                "role": WorkShiftEntry.Role.WORKING_STUDENT,
                "clock_in": timezone.localtime(self.shift.clock_in).strftime("%Y-%m-%dT%H:%M"),
                "clock_out": timezone.localtime(new_clock_out).strftime("%Y-%m-%dT%H:%M"),
                "notes": "Manager correction",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.shift.refresh_from_db()
        self.assertEqual(self.shift.notes, "Manager correction")
        self.assertEqual(
            self.shift.clock_out.replace(second=0, microsecond=0),
            new_clock_out.replace(second=0, microsecond=0),
        )
        self.assertTrue(
            AuditEvent.objects.filter(
                team=self.team,
                actor=self.admin,
                action="station_shift_corrected",
                entity_id=self.shift.pk,
            ).exists()
        )
        self.assertEqual(
            self.client.get(reverse("station_shift_edit", args=[self.other_shift.pk])).status_code,
            404,
        )
