from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.people import (
    Committee,
    CommitteeMembership,
    OrganizationGroup,
    OrganizationRoleAssignment,
    Person,
    PersonRelationship,
)
from portal.models import Team, UserProfile


class V320PeopleRelationshipsTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
        self.other_team = Team.objects.create(name="Other Barn")
        self.admin = User.objects.create_user(username="admin-rel-v320", password="pass12345")
        UserProfile.objects.create(user=self.admin, team=self.team, role=UserProfile.Role.ADMIN)
        self.person = Person.objects.create(team=self.team, first_name="Jane", last_name="Smith")
        self.child = Person.objects.create(team=self.team, first_name="Emma", last_name="Smith")
        self.outsider = Person.objects.create(team=self.other_team, first_name="Other", last_name="Person")
        self.client.force_login(self.admin)

    def test_person_can_hold_multiple_roles(self):
        for role in (
            OrganizationRoleAssignment.Role.RIDER,
            OrganizationRoleAssignment.Role.BOARDER,
            OrganizationRoleAssignment.Role.BOARD_MEMBER,
        ):
            response = self.client.post(
                reverse("person_role_add", args=[self.person.pk]),
                {"role": role, "active": "on"},
            )
            self.assertEqual(response.status_code, 302)
        self.assertEqual(self.person.role_assignments.filter(active=True).count(), 3)

    def test_parent_relationship_is_directional(self):
        response = self.client.post(
            reverse("person_relationship_add", args=[self.person.pk]),
            {
                "to_person": self.child.pk,
                "relationship_type": PersonRelationship.RelationshipType.PARENT_GUARDIAN,
                "label": "Mother",
                "primary_contact": "on",
                "active": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        relationship = PersonRelationship.objects.get(from_person=self.person, to_person=self.child)
        self.assertEqual(relationship.label, "Mother")
        self.assertTrue(relationship.primary_contact)

    def test_relationship_form_rejects_other_organization_person(self):
        response = self.client.post(
            reverse("person_relationship_add", args=[self.person.pk]),
            {
                "to_person": self.outsider.pk,
                "relationship_type": PersonRelationship.RelationshipType.PARENT_GUARDIAN,
                "active": "on",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Select a valid choice")
        self.assertFalse(PersonRelationship.objects.filter(from_person=self.person).exists())

    def test_group_and_scoped_committee_can_be_created(self):
        response = self.client.post(
            reverse("organization_group_add"),
            {"name": "IEA Program", "group_type": OrganizationGroup.GroupType.PROGRAM, "active": "on", "sort_order": 0},
        )
        self.assertEqual(response.status_code, 302)
        group = OrganizationGroup.objects.get(team=self.team, name="IEA Program")
        response = self.client.post(
            reverse("committee_add"),
            {"name": "Events Committee", "group": group.pk, "active": "on", "sort_order": 0},
        )
        self.assertEqual(response.status_code, 302)
        committee = Committee.objects.get(team=self.team, name="Events Committee")
        self.assertEqual(committee.group, group)

    def test_committee_membership_is_person_based(self):
        committee = Committee.objects.create(team=self.team, name="Finance Committee")
        response = self.client.post(
            reverse("person_committee_add", args=[self.person.pk]),
            {
                "committee": committee.pk,
                "position": CommitteeMembership.Position.TREASURER,
                "active": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        membership = CommitteeMembership.objects.get(person=self.person, committee=committee)
        self.assertEqual(membership.position, CommitteeMembership.Position.TREASURER)

    def test_structure_page_is_manager_only(self):
        member = User.objects.create_user(username="member-rel-v320", password="pass12345")
        UserProfile.objects.create(user=member, team=self.team, role=UserProfile.Role.PARENT)
        Person.objects.create(team=self.team, user=member, first_name="Parent", last_name="Member")
        self.client.force_login(member)
        response = self.client.get(reverse("people_structure"))
        self.assertEqual(response.status_code, 403)
