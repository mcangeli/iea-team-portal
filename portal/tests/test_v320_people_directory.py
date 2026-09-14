from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.people import OrganizationRoleAssignment, Person
from portal.models import Team, UserProfile
from portal.people_forms import PersonForm


class V320PeopleDirectoryTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
        self.other_team = Team.objects.create(name="Other Barn")

        self.admin = User.objects.create_user(
            username="admin-v320", password="pass12345", first_name="Admin", last_name="User"
        )
        UserProfile.objects.create(user=self.admin, team=self.team, role=UserProfile.Role.ADMIN)

        self.member = User.objects.create_user(
            username="member-v320", password="pass12345", first_name="Jamie", last_name="Rider"
        )
        UserProfile.objects.create(user=self.member, team=self.team, role=UserProfile.Role.RIDER)

        self.other_user = User.objects.create_user(
            username="other-v320", password="pass12345", first_name="Other", last_name="User"
        )
        UserProfile.objects.create(user=self.other_user, team=self.other_team, role=UserProfile.Role.ADMIN)

        self.person = Person.objects.create(
            team=self.team,
            user=self.member,
            first_name="Jamie",
            last_name="Rider",
            email="private@example.com",
            phone="555-0100",
            school="Example School",
            graduation_year=2028,
        )
        OrganizationRoleAssignment.objects.create(
            team=self.team,
            person=self.person,
            role=OrganizationRoleAssignment.Role.RIDER,
        )

    def test_authenticated_member_can_view_people_directory(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("people_directory"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "People directory")
        self.assertContains(response, "Jamie Rider")
        self.assertContains(response, "Rider")

    def test_person_can_view_their_private_profile_fields(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("person_detail", args=[self.person.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "private@example.com")
        self.assertContains(response, "member-v320")

    def test_other_non_manager_does_not_receive_private_fields(self):
        peer_user = User.objects.create_user(username="peer-v320", password="pass12345")
        UserProfile.objects.create(user=peer_user, team=self.team, role=UserProfile.Role.PARENT)
        Person.objects.create(team=self.team, user=peer_user, first_name="Peer", last_name="Parent")
        self.client.force_login(peer_user)
        response = self.client.get(reverse("person_detail", args=[self.person.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "private@example.com")
        self.assertNotContains(response, "555-0100")
        self.assertNotContains(response, "member-v320")

    def test_manager_can_create_person_and_attach_same_team_django_account(self):
        unused_user = User.objects.create_user(username="new-person-v320", password="pass12345")
        UserProfile.objects.create(user=unused_user, team=self.team, role=UserProfile.Role.PARENT)
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("person_create"),
            {
                "user": unused_user.pk,
                "first_name": "Taylor",
                "last_name": "Parent",
                "email": "taylor@example.com",
                "active": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        created = Person.objects.get(first_name="Taylor", last_name="Parent")
        self.assertEqual(created.user, unused_user)
        self.assertEqual(created.team, self.team)

    def test_person_form_never_offers_other_organization_django_accounts(self):
        form = PersonForm(team=self.team)
        user_ids = set(form.fields["user"].queryset.values_list("id", flat=True))
        self.assertIn(self.admin.id, user_ids)
        self.assertIn(self.member.id, user_ids)
        self.assertNotIn(self.other_user.id, user_ids)

    def test_person_routes_are_tenant_scoped(self):
        outsider_person = Person.objects.create(
            team=self.other_team,
            first_name="Outside",
            last_name="Person",
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse("person_detail", args=[outsider_person.pk]))
        self.assertEqual(response.status_code, 404)
