from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from portal.model_modules.people import Person, PersonRelationship
from portal.model_modules.station import WorkShiftEntry
from portal.models import Team, UserProfile


class V323PeopleWorkHistoryTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
        self.admin = User.objects.create_user(username="work-admin", password="pass12345")
        profile = self.admin.profile
        profile.team = self.team
        profile.role = UserProfile.Role.ADMIN
        profile.save(update_fields=["team", "role"])
        self.person = Person.objects.create(team=self.team, first_name="Jamie", last_name="Worker")

    def _shift(self, *, role=WorkShiftEntry.Role.WORKING_STUDENT, minutes=90, approved=False, open_shift=False):
        clock_in = timezone.now() - timedelta(hours=3)
        shift = WorkShiftEntry.objects.create(
            team=self.team,
            person=self.person,
            role=role,
            clock_in=clock_in,
            clock_out=None if open_shift else clock_in + timedelta(minutes=minutes),
        )
        if approved:
            shift.approved_by = self.admin
            shift.approved_at = timezone.now()
            shift.save(update_fields=["approved_by", "approved_at", "updated_at"])
        return shift

    def test_manager_person_profile_summarizes_station_work(self):
        self._shift(minutes=90, approved=True)
        self._shift(role=WorkShiftEntry.Role.BARN_STAFF, minutes=45)
        self._shift(open_shift=True)
        self.client.force_login(self.admin)
        response = self.client.get(reverse("person_detail", args=[self.person.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Work history")
        self.assertContains(response, "2h 15m")
        self.assertContains(response, "1h 30m")
        self.assertContains(response, "Needs review")
        self.assertContains(response, "Open")
        self.assertEqual(response.context["work_summary"]["completed_count"], 2)
        self.assertEqual(response.context["work_summary"]["pending_count"], 1)
        self.assertEqual(response.context["work_summary"]["open_count"], 1)

    def test_person_can_view_own_work_history(self):
        worker = User.objects.create_user(username="worker-self", password="pass12345")
        profile = worker.profile
        profile.team = self.team
        profile.role = UserProfile.Role.RIDER
        profile.save(update_fields=["team", "role"])
        self.person.user = worker
        self.person.save(update_fields=["user", "updated_at"])
        self._shift(minutes=60, approved=True)
        self.client.force_login(worker)
        response = self.client.get(reverse("person_detail", args=[self.person.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Work history")
        self.assertEqual(response.context["work_summary"]["completed_count"], 1)

    def test_parent_private_profile_access_does_not_expose_work_history(self):
        parent_user = User.objects.create_user(username="work-parent", password="pass12345")
        profile = parent_user.profile
        profile.team = self.team
        profile.role = UserProfile.Role.PARENT
        profile.save(update_fields=["team", "role"])
        parent = Person.objects.create(team=self.team, user=parent_user, first_name="Morgan", last_name="Parent")
        PersonRelationship.objects.create(
            from_person=parent,
            to_person=self.person,
            relationship_type=PersonRelationship.RelationshipType.PARENT_GUARDIAN,
            active=True,
        )
        self._shift(minutes=60, approved=True)
        self.client.force_login(parent_user)
        response = self.client.get(reverse("person_detail", args=[self.person.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["can_view_private"])
        self.assertFalse(response.context["can_view_work_history"])
        self.assertNotContains(response, "Work history")
        self.assertIsNone(response.context["work_summary"])

    def test_work_history_is_not_exposed_without_private_person_access(self):
        self._shift(minutes=60, approved=True)
        outsider = User.objects.create_user(username="outside-rider", password="pass12345")
        profile = outsider.profile
        profile.team = self.team
        profile.role = UserProfile.Role.RIDER
        profile.save(update_fields=["team", "role"])
        self.client.force_login(outsider)
        response = self.client.get(reverse("person_detail", args=[self.person.pk]))
        if response.status_code == 200:
            self.assertNotContains(response, "Work history")
            self.assertIsNone(response.context.get("work_summary"))
        else:
            self.assertEqual(response.status_code, 404)
