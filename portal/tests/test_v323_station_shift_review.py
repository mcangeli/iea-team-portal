from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from portal.model_modules.people import Person
from portal.model_modules.station import WorkShiftEntry
from portal.models import AuditEvent, Team, UserProfile


class V323StationShiftReviewTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
        self.other_team = Team.objects.create(name="Other Barn")
        self.admin = User.objects.create_user(username="shift-admin", password="pass12345")
        profile = self.admin.profile
        profile.team = self.team
        profile.role = UserProfile.Role.ADMIN
        profile.save(update_fields=["team", "role"])
        self.person = Person.objects.create(team=self.team, first_name="Jamie", last_name="Worker")

    def _shift(self, *, team=None, person=None, closed=True):
        team = team or self.team
        person = person or self.person
        clock_in = timezone.now() - timedelta(hours=2)
        return WorkShiftEntry.objects.create(
            team=team,
            person=person,
            role=WorkShiftEntry.Role.WORKING_STUDENT,
            clock_in=clock_in,
            clock_out=clock_in + timedelta(minutes=90) if closed else None,
        )

    def test_manager_can_approve_closed_shift_and_audit_is_created(self):
        shift = self._shift()
        self.client.force_login(self.admin)
        response = self.client.post(reverse("station_shift_approve", args=[shift.pk]))
        self.assertRedirects(response, reverse("station_shift_review"))
        shift.refresh_from_db()
        self.assertEqual(shift.approved_by, self.admin)
        self.assertIsNotNone(shift.approved_at)
        self.assertTrue(
            AuditEvent.objects.filter(
                team=self.team,
                actor=self.admin,
                action="station_shift_approved",
                entity_type="WorkShiftEntry",
                entity_id=shift.pk,
            ).exists()
        )

    def test_open_shift_cannot_be_approved(self):
        shift = self._shift(closed=False)
        self.client.force_login(self.admin)
        response = self.client.post(reverse("station_shift_approve", args=[shift.pk]))
        self.assertRedirects(response, reverse("station_shift_review"))
        shift.refresh_from_db()
        self.assertIsNone(shift.approved_by)
        self.assertIsNone(shift.approved_at)
        self.assertFalse(AuditEvent.objects.filter(action="station_shift_approved", entity_id=shift.pk).exists())

    def test_shift_approval_is_cross_organization_isolated(self):
        other_person = Person.objects.create(team=self.other_team, first_name="Other", last_name="Worker")
        shift = self._shift(team=self.other_team, person=other_person)
        self.client.force_login(self.admin)
        response = self.client.post(reverse("station_shift_approve", args=[shift.pk]))
        self.assertEqual(response.status_code, 404)
        shift.refresh_from_db()
        self.assertIsNone(shift.approved_at)

    def test_non_manager_cannot_open_shift_review(self):
        rider = User.objects.create_user(username="shift-rider", password="pass12345")
        profile = rider.profile
        profile.team = self.team
        profile.role = UserProfile.Role.RIDER
        profile.save(update_fields=["team", "role"])
        self.client.force_login(rider)
        response = self.client.get(reverse("station_shift_review"))
        self.assertIn(response.status_code, (403, 404))

    def test_export_contains_only_callers_organization_and_is_audited(self):
        own_shift = self._shift()
        other_person = Person.objects.create(team=self.other_team, first_name="Other", last_name="Worker")
        self._shift(team=self.other_team, person=other_person)
        self.client.force_login(self.admin)
        response = self.client.get(reverse("station_shift_export"))
        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8")
        self.assertIn(own_shift.person.display_name, body)
        self.assertNotIn(other_person.display_name, body)
        self.assertTrue(
            AuditEvent.objects.filter(
                team=self.team,
                actor=self.admin,
                action="station_shift_exported",
                entity_type="WorkShiftEntry",
            ).exists()
        )
