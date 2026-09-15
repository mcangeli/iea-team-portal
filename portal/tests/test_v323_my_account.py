from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.people import OrganizationRoleAssignment, Person
from portal.models import Team, UserProfile


class V323MyAccountTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
        self.user = User.objects.create_user(username="my-rider", email="old@example.com", password="pass12345")
        profile = self.user.profile
        profile.team = self.team
        profile.role = UserProfile.Role.RIDER
        profile.save(update_fields=["team", "role"])
        self.person = Person.objects.create(
            team=self.team,
            user=self.user,
            first_name="Jamie",
            last_name="Rider",
            email="old@example.com",
            school="Old School",
            graduation_year=2028,
        )
        OrganizationRoleAssignment.objects.create(team=self.team, person=self.person, role=OrganizationRoleAssignment.Role.RIDER)

    def test_logged_in_person_can_open_my_account(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("my_account"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My Account")
        self.assertContains(response, "Roles &amp; responsibilities")
        self.assertContains(response, "Birthday")

    def test_user_can_update_only_self_service_profile_fields(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("my_account"),
            {
                "preferred_name": "Jay",
                "email": "jay@example.com",
                "phone": "555-0100",
                "school": "New School",
                "graduation_year": "2029",
                "bio": "Rider bio",
                "website_url": "",
                "instagram_url": "https://instagram.com/jay",
                "facebook_url": "",
                "tiktok_url": "",
                "youtube_url": "",
                "public_profile_enabled": "on",
                "first_name": "Changed",
                "last_name": "Name",
                "birth_date": "2000-01-01",
                "active": "",
            },
        )
        self.assertRedirects(response, reverse("my_account"))
        self.person.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(self.person.preferred_name, "Jay")
        self.assertEqual(self.person.email, "jay@example.com")
        self.assertEqual(self.user.email, "jay@example.com")
        self.assertEqual(self.person.school, "New School")
        self.assertEqual(self.person.graduation_year, 2029)
        self.assertEqual(self.person.first_name, "Jamie")
        self.assertEqual(self.person.last_name, "Rider")
        self.assertIsNone(self.person.birth_date)
        self.assertTrue(self.person.active)

    def test_my_account_form_does_not_expose_managed_fields(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("my_account"))
        fields = response.context["form"].fields
        self.assertNotIn("first_name", fields)
        self.assertNotIn("last_name", fields)
        self.assertNotIn("birth_date", fields)
        self.assertNotIn("user", fields)
        self.assertNotIn("active", fields)

    def test_account_without_person_identity_gets_safe_unavailable_page(self):
        orphan = User.objects.create_user(username="orphan-account", password="pass12345")
        profile = orphan.profile
        profile.team = self.team
        profile.role = UserProfile.Role.PARENT
        profile.save(update_fields=["team", "role"])
        self.client.force_login(orphan)
        response = self.client.get(reverse("my_account"))
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Profile not available yet", status_code=404)
