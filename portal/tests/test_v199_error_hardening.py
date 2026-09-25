from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.people import Person
from portal.models import Rider, Team, UserProfile


class V199ErrorHardeningTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Hardening Team")
        self.admin = User.objects.create_user(username="hardening-admin", password="testpass")
        self.admin.profile.team = self.team
        self.admin.profile.role = UserProfile.Role.ADMIN
        self.admin.profile.save(update_fields=["team", "role"])
        self.rider = Rider.objects.create(
            team=self.team,
            first_name="Emma",
            last_name="Brown",
        )
        self.parent = Person.objects.create(team=self.team, first_name="Alex", last_name="Brown")
        self.client.force_login(self.admin)

    def test_guardian_link_empty_submission_redirects_with_message(self):
        response = self.client.post(
            reverse("rider_guardian_link", args=[self.rider.pk]),
            {},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Choose an existing person or login account.")
        self.assertEqual(self.rider.guardian_links.count(), 0)

    def test_guardian_link_duplicate_is_idempotent(self):
        url = reverse("rider_guardian_link", args=[self.rider.pk])
        payload = {"person": f"person:{self.parent.pk}", "relationship": "Parent/Guardian"}

        first = self.client.post(url, payload, follow=True)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(
            self.parent.outgoing_relationships.filter(
                to_person=self.rider.person_bridge.person,
                relationship_type="parent_guardian",
                active=True,
            ).count(),
            1,
        )

        second = self.client.post(url, payload, follow=True)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(self.rider.guardian_links.count(), 1)
