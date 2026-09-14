from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.people import OrganizationRoleAssignment, Person
from portal.model_modules.station import StationCredential, StationDevice, WorkShiftEntry
from portal.models import Team, UserProfile


class V322StationUITests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
        self.other_team = Team.objects.create(name="Other Barn")

        self.admin = User.objects.create_user(username="station-admin", password="pass12345")
        self._configure_profile(self.admin, self.team, UserProfile.Role.ADMIN)
        self.member = User.objects.create_user(username="station-member", password="pass12345")
        self._configure_profile(self.member, self.team, UserProfile.Role.PARENT)

        self.person = Person.objects.create(team=self.team, first_name="Jamie", last_name="Smith")
        self.outsider = Person.objects.create(team=self.other_team, first_name="Taylor", last_name="Jones")

        for role in (
            OrganizationRoleAssignment.Role.WORKING_STUDENT,
            OrganizationRoleAssignment.Role.ASSISTANT_TRAINER,
        ):
            OrganizationRoleAssignment.objects.create(
                team=self.team,
                person=self.person,
                role=role,
                active=True,
            )

    @staticmethod
    def _configure_profile(user, team, role):
        profile = user.profile
        profile.team = team
        profile.role = role
        profile.save(update_fields=["team", "role"])

    def _device(self):
        device = StationDevice(team=self.team, name="Barn iPad")
        device.set_secret("station-secret-12345")
        device.save()
        return device

    def _credential(self, person=None, team=None, pin="2468"):
        person = person or self.person
        team = team or person.team
        credential = StationCredential(team=team, person=person, active=True)
        credential.set_pin(pin)
        credential.full_clean()
        credential.save()
        return credential

    def _activate(self, device=None):
        device = device or self._device()
        response = self.client.post(
            reverse("station_activate"),
            {"device_key": device.device_key, "secret": "station-secret-12345"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("station_home"))
        return device

    def _identify(self, pin="2468"):
        response = self.client.post(
            reverse("station_identify", args=[self.person.pk]),
            {"person_id": self.person.pk, "pin": pin},
        )
        return response

    def test_manager_can_register_device_and_secret_is_one_time(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("station_device_add"),
            {"name": "Front Barn iPad", "notes": "Mounted by office", "active": "on"},
        )
        self.assertEqual(response.status_code, 200)
        device = StationDevice.objects.get(team=self.team, name="Front Barn iPad")
        raw_secret = response.context["raw_secret"]
        self.assertTrue(device.device_key)
        self.assertTrue(device.check_secret(raw_secret))
        self.assertNotEqual(device.secret_hash, raw_secret)
        self.assertContains(response, "One-time secret")

    def test_station_management_is_manager_only(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("station_manage"))
        self.assertEqual(response.status_code, 403)

    def test_manager_can_set_person_station_pin(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("station_person_pin", args=[self.person.pk]),
            {"pin": "8642", "active": "on"},
        )
        self.assertEqual(response.status_code, 302)
        credential = StationCredential.objects.get(person=self.person)
        self.assertTrue(credential.check_pin("8642"))
        self.assertNotEqual(credential.pin_hash, "8642")

    def test_device_activation_and_home_are_tenant_scoped(self):
        device = self._device()
        self._credential()
        outsider_credential = self._credential(person=self.outsider, pin="1357")
        self._activate(device)
        response = self.client.get(reverse("station_home"))
        self.assertContains(response, self.person.display_name)
        self.assertNotContains(response, self.outsider.display_name)
        response = self.client.get(reverse("station_identify", args=[outsider_credential.person_id]))
        self.assertEqual(response.status_code, 404)

    def test_wrong_pin_does_not_create_station_identity_session(self):
        device = self._device()
        self._credential()
        self._activate(device)
        response = self._identify(pin="9999")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "That PIN is not correct")
        response = self.client.get(reverse("station_action"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("station_home"))

    def test_person_with_multiple_work_roles_can_choose_shift_role(self):
        device = self._device()
        self._credential()
        self._activate(device)
        response = self._identify()
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse("station_action"))
        self.assertContains(response, "Working Student")
        self.assertContains(response, "Assistant Trainer")

        response = self.client.post(
            reverse("station_action"),
            {"action": "clock_in", "role": WorkShiftEntry.Role.ASSISTANT_TRAINER},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You are clocked in")
        shift = WorkShiftEntry.objects.get(person=self.person, clock_out__isnull=True)
        self.assertEqual(shift.station, device)
        self.assertEqual(shift.role, WorkShiftEntry.Role.ASSISTANT_TRAINER)

    def test_clock_out_closes_existing_shift(self):
        device = self._device()
        self._credential()
        self._activate(device)
        self._identify()
        self.client.post(
            reverse("station_action"),
            {"action": "clock_in", "role": WorkShiftEntry.Role.WORKING_STUDENT},
        )
        shift = WorkShiftEntry.objects.get(person=self.person, clock_out__isnull=True)

        self.client.get(reverse("station_home"))
        self._identify()
        response = self.client.post(reverse("station_action"), {"action": "clock_out"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You are clocked out")
        shift.refresh_from_db()
        self.assertIsNotNone(shift.clock_out)
