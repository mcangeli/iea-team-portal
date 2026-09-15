from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from portal.model_modules.people import OrganizationRoleAssignment, Person
from portal.model_modules.station import StationCredential, StationDevice, WorkShiftEntry
from portal.models import AuditEvent, Team, UserProfile


class V322StationHardeningTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
        self.other_team = Team.objects.create(name="Other Barn")
        self.admin = User.objects.create_user(username="station-hardening-admin", password="pass12345")
        profile = self.admin.profile
        profile.team = self.team
        profile.role = UserProfile.Role.ADMIN
        profile.save(update_fields=["team", "role"])

        self.person = Person.objects.create(team=self.team, first_name="Jamie", last_name="Smith")
        self.other_person = Person.objects.create(team=self.other_team, first_name="Taylor", last_name="Jones")
        OrganizationRoleAssignment.objects.create(
            team=self.team,
            person=self.person,
            role=OrganizationRoleAssignment.Role.WORKING_STUDENT,
            active=True,
        )
        self.device = StationDevice(team=self.team, name="Barn iPad")
        self.device.set_secret("station-secret-12345")
        self.device.save()
        self.credential = StationCredential(team=self.team, person=self.person, active=True)
        self.credential.set_pin("2468")
        self.credential.full_clean()
        self.credential.save()

    def _activate(self):
        response = self.client.post(
            reverse("station_activate"),
            {"device_key": self.device.device_key, "secret": "station-secret-12345"},
        )
        self.assertEqual(response.status_code, 302)

    def _identify(self, pin="2468"):
        return self.client.post(
            reverse("station_identify", args=[self.person.pk]),
            {"person_id": self.person.pk, "pin": pin},
        )

    def test_pin_is_temporarily_locked_after_five_failures(self):
        self._activate()
        response = None
        for _ in range(5):
            response = self._identify(pin="9999")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "temporarily locked")
        self.assertTrue(
            AuditEvent.objects.filter(
                team=self.team,
                action="station_pin_locked",
                entity_type="Person",
                entity_id=self.person.pk,
            ).exists()
        )

        response = self._identify(pin="2468")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Too many incorrect PIN attempts")
        self.assertNotIn("arenaline_station_person_id", self.client.session)

    def test_clock_in_and_out_create_audit_events(self):
        self._activate()
        self.assertEqual(self._identify().status_code, 302)
        response = self.client.post(
            reverse("station_action"),
            {"action": "clock_in", "role": WorkShiftEntry.Role.WORKING_STUDENT},
        )
        self.assertEqual(response.status_code, 200)
        shift = WorkShiftEntry.objects.get(person=self.person, clock_out__isnull=True)
        self.assertTrue(
            AuditEvent.objects.filter(
                team=self.team,
                action="station_clock_in",
                entity_id=shift.pk,
            ).exists()
        )

        self.client.get(reverse("station_home"))
        self._identify()
        response = self.client.post(reverse("station_action"), {"action": "clock_out"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            AuditEvent.objects.filter(
                team=self.team,
                action="station_clock_out",
                entity_id=shift.pk,
            ).exists()
        )

    def test_manager_device_and_pin_changes_are_audited_without_raw_secrets(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("station_device_add"),
            {"name": "Office iPad", "notes": "Front office", "active": "on"},
        )
        self.assertEqual(response.status_code, 200)
        device = StationDevice.objects.get(team=self.team, name="Office iPad")
        event = AuditEvent.objects.get(action="station_device_added", entity_id=device.pk)
        self.assertNotIn("secret", str(event.details).lower())

        response = self.client.post(
            reverse("station_person_pin", args=[self.person.pk]),
            {"pin": "8642", "active": "on"},
        )
        self.assertEqual(response.status_code, 302)
        pin_event = AuditEvent.objects.filter(action="station_pin_updated", entity_id=self.credential.pk).latest("id")
        self.assertNotIn("8642", str(pin_event.details))

    def test_staff_hours_export_is_tenant_scoped_and_audited(self):
        now = timezone.now().replace(second=0, microsecond=0)
        WorkShiftEntry.objects.create(
            team=self.team,
            person=self.person,
            role=WorkShiftEntry.Role.WORKING_STUDENT,
            clock_in=now - timedelta(hours=2),
            clock_out=now,
        )
        WorkShiftEntry.objects.create(
            team=self.other_team,
            person=self.other_person,
            role=WorkShiftEntry.Role.BARN_STAFF,
            clock_in=now - timedelta(hours=1),
            clock_out=now,
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse("station_shift_export"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        body = response.content.decode("utf-8")
        self.assertIn(self.person.display_name, body)
        self.assertIn("Working Student", body)
        self.assertNotIn(self.other_person.display_name, body)
        self.assertTrue(
            AuditEvent.objects.filter(
                team=self.team,
                actor=self.admin,
                action="station_shift_exported",
            ).exists()
        )
