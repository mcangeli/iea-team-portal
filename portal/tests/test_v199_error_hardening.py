from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.models import GuardianContact, Rider, Team, UserProfile


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
        self.client.force_login(self.admin)

    def test_guardian_link_empty_submission_redirects_with_message(self):
        response = self.client.post(
            reverse("rider_guardian_link", args=[self.rider.pk]),
            {},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Choose a parent/guardian to link.")
        self.assertEqual(self.rider.guardian_links.count(), 0)

    def test_guardian_link_duplicate_is_idempotent(self):
        guardian = GuardianContact.objects.create(
            team=self.team,
            first_name="Alex",
            last_name="Brown",
        )
        url = reverse("rider_guardian_link", args=[self.rider.pk])
        payload = {"guardian": guardian.pk, "relationship": "Parent/Guardian"}

        first = self.client.post(url, payload, follow=True)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(self.rider.guardian_links.count(), 1)

        second = self.client.post(url, payload, follow=True)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(self.rider.guardian_links.count(), 1)
