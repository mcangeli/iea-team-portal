from datetime import timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from portal.model_modules.people import Person
from portal.model_modules.station import StationCredential, StationDevice, WorkShiftEntry
from portal.models import Team, UserProfile


class V322StationFoundationTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
        self.other_team = Team.objects.create(name="Other Barn")
        self.person = Person.objects.create(
            team=self.team,
            first_name="Jamie",
            last_name="Smith",
        )
        self.other_person = Person.objects.create(
            team=self.other_team,
            first_name="Taylor",
            last_name="Jones",
        )

    def test_station_device_secret_is_hashed_and_verifiable(self):
        device = StationDevice(team=self.team, name="Barn iPad")
        device.set_secret("station-secret-12345")
        device.save()
        self.assertTrue(device.device_key)
        self.assertNotEqual(device.secret_hash, "station-secret-12345")
        self.assertTrue(device.check_secret("station-secret-12345"))
        self.assertFalse(device.check_secret("wrong-secret"))

    def test_station_credential_does_not_require_django_login(self):
        credential = StationCredential(team=self.team, person=self.person)
        credential.set_pin("2468")
        credential.full_clean()
        credential.save()
        self.assertIsNone(self.person.user_id)
        self.assertNotEqual(credential.pin_hash, "2468")
        self.assertTrue(credential.check_pin("2468"))
        self.assertFalse(credential.check_pin("1357"))

    def test_station_pin_must_be_4_to_8_digits(self):
        credential = StationCredential(team=self.team, person=self.person)
        for bad_pin in ("123", "123456789", "12ab"):
            with self.assertRaises(ValidationError):
                credential.set_pin(bad_pin)

    def test_station_credential_rejects_cross_organization_person(self):
        credential = StationCredential(team=self.team, person=self.other_person)
        credential.set_pin("2468")
        with self.assertRaises(ValidationError):
            credential.full_clean()

    def test_work_shift_rejects_cross_organization_station_or_person(self):
        device = StationDevice(team=self.team, name="Barn iPad")
        device.set_secret("station-secret-12345")
        device.save()
        other_device = StationDevice(team=self.other_team, name="Other iPad")
        other_device.set_secret("other-station-secret")
        other_device.save()
        now = timezone.now()

        cross_person = WorkShiftEntry(team=self.team, person=self.other_person, station=device, clock_in=now)
        with self.assertRaises(ValidationError):
            cross_person.full_clean()

        cross_station = WorkShiftEntry(team=self.team, person=self.person, station=other_device, clock_in=now)
        with self.assertRaises(ValidationError):
            cross_station.full_clean()

    def test_clock_out_cannot_precede_clock_in(self):
        now = timezone.now()
        shift = WorkShiftEntry(
            team=self.team,
            person=self.person,
            clock_in=now,
            clock_out=now - timedelta(minutes=5),
        )
        with self.assertRaises(ValidationError):
            shift.full_clean()

    def test_only_one_open_shift_per_person(self):
        now = timezone.now()
        WorkShiftEntry.objects.create(team=self.team, person=self.person, clock_in=now)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                WorkShiftEntry.objects.create(
                    team=self.team,
                    person=self.person,
                    clock_in=now + timedelta(minutes=1),
                )

    def test_shift_approver_cannot_cross_organization_boundary(self):
        approver = User.objects.create_user(username="other-manager", password="pass12345")
        profile = UserProfile.objects.get(user=approver)
        profile.team = self.other_team
        profile.role = UserProfile.Role.ADMIN
        profile.save(update_fields=["team", "role"])
        shift = WorkShiftEntry(
            team=self.team,
            person=self.person,
            clock_in=timezone.now(),
            approved_by=approver,
        )
        with self.assertRaises(ValidationError):
            shift.full_clean()
