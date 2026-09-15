from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.people import Committee, CommitteeMembership, OrganizationGroup, Person
from portal.models import Team, UserProfile


class V323PeopleStructureTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
        self.other_team = Team.objects.create(name="Other Barn")
        self.admin = User.objects.create_user(username="structure-admin", password="pass12345")
        profile = self.admin.profile
        profile.team = self.team
        profile.role = UserProfile.Role.ADMIN
        profile.save(update_fields=["team", "role"])
        self.group = OrganizationGroup.objects.create(team=self.team, name="IEA Program", group_type=OrganizationGroup.GroupType.PROGRAM)
        self.person = Person.objects.create(team=self.team, first_name="Morgan", last_name="Leader")
        self.committee = Committee.objects.create(team=self.team, group=self.group, name="Show Committee")
        CommitteeMembership.objects.create(committee=self.committee, person=self.person, position=CommitteeMembership.Position.CHAIR)

    def test_people_directory_exposes_structure_for_manager(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("people_directory"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Groups &amp; committees", html=False)
        self.assertContains(response, reverse("people_structure"))

    def test_structure_links_to_group_and_committee_dashboards(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("people_structure"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("organization_group_detail", args=[self.group.pk]))
        self.assertContains(response, reverse("committee_detail", args=[self.committee.pk]))

    def test_group_dashboard_shows_scoped_committee_and_member(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("organization_group_detail", args=[self.group.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "IEA Program")
        self.assertContains(response, "Show Committee")
        self.assertContains(response, "Morgan Leader")

    def test_committee_dashboard_shows_active_leadership(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("committee_detail", args=[self.committee.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Show Committee")
        self.assertContains(response, "Morgan Leader")
        self.assertContains(response, "Chair")

    def test_structure_dashboards_are_cross_organization_isolated(self):
        other_group = OrganizationGroup.objects.create(team=self.other_team, name="Private Program")
        other_committee = Committee.objects.create(team=self.other_team, group=other_group, name="Private Committee")
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("organization_group_detail", args=[other_group.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("committee_detail", args=[other_committee.pk])).status_code, 404)

    def test_non_manager_cannot_open_structure_administration(self):
        rider = User.objects.create_user(username="structure-rider", password="pass12345")
        profile = rider.profile
        profile.team = self.team
        profile.role = UserProfile.Role.RIDER
        profile.save(update_fields=["team", "role"])
        self.client.force_login(rider)
        response = self.client.get(reverse("people_structure"))
        self.assertIn(response.status_code, (403, 404))
