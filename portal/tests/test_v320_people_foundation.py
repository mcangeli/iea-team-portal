from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from portal.model_modules.people import (
    Committee,
    CommitteeMembership,
    LegacyPersonLink,
    OrganizationGroup,
    OrganizationRoleAssignment,
    Person,
    PersonRelationship,
)
from portal.models import GuardianContact, Rider, Team


class V320PeopleFoundationTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
        self.other_team = Team.objects.create(name="Other Barn")

    def test_person_uses_one_optional_django_auth_account(self):
        user = User.objects.create_user(
            username="jane",
            password="testpass",
            first_name="Jane",
            last_name="Smith",
        )
        user.profile.team = self.team
        user.profile.save(update_fields=["team"])

        person = Person.objects.create(
            team=self.team,
            user=user,
            first_name="Jane",
            last_name="Smith",
        )

        self.assertEqual(user.arena_person, person)
        with self.assertRaises(IntegrityError):
            Person.objects.create(
                team=self.team,
                user=user,
                first_name="Duplicate",
                last_name="Identity",
            )

    def test_person_can_bridge_both_legacy_rider_and_guardian_records(self):
        user = User.objects.create_user(username="alex", password="testpass")
        user.profile.team = self.team
        user.profile.save(update_fields=["team"])
        rider = Rider.objects.create(
            team=self.team,
            user=user,
            first_name="Alex",
            last_name="Morgan",
        )
        guardian = GuardianContact.objects.create(
            team=self.team,
            first_name="Alex",
            last_name="Morgan",
        )
        person = Person.objects.create(
            team=self.team,
            user=user,
            first_name="Alex",
            last_name="Morgan",
        )

        bridge = LegacyPersonLink.objects.create(
            person=person,
            rider=rider,
            guardian=guardian,
        )

        self.assertEqual(bridge.rider, rider)
        self.assertEqual(bridge.guardian, guardian)

    def test_person_supports_multiple_simultaneous_organization_roles(self):
        person = Person.objects.create(
            team=self.team,
            first_name="Taylor",
            last_name="Jones",
        )
        OrganizationRoleAssignment.objects.create(
            team=self.team,
            person=person,
            role=OrganizationRoleAssignment.Role.RIDER,
        )
        OrganizationRoleAssignment.objects.create(
            team=self.team,
            person=person,
            role=OrganizationRoleAssignment.Role.BOARDER,
        )
        OrganizationRoleAssignment.objects.create(
            team=self.team,
            person=person,
            role=OrganizationRoleAssignment.Role.BOARD_MEMBER,
        )

        self.assertEqual(person.role_assignments.filter(active=True).count(), 3)

    def test_parent_relationship_is_directional_and_org_scoped(self):
        parent = Person.objects.create(
            team=self.team,
            first_name="Jordan",
            last_name="Parent",
        )
        youth = Person.objects.create(
            team=self.team,
            first_name="Sam",
            last_name="Rider",
        )
        relation = PersonRelationship.objects.create(
            from_person=parent,
            to_person=youth,
            relationship_type=PersonRelationship.RelationshipType.PARENT_GUARDIAN,
            label="Parent",
            primary_contact=True,
        )
        self.assertEqual(relation.from_person, parent)
        self.assertEqual(relation.to_person, youth)

        outsider = Person.objects.create(
            team=self.other_team,
            first_name="Other",
            last_name="Person",
        )
        invalid = PersonRelationship(
            from_person=parent,
            to_person=outsider,
            relationship_type=PersonRelationship.RelationshipType.PARENT_GUARDIAN,
        )
        with self.assertRaises(ValidationError):
            invalid.full_clean()

    def test_committees_can_be_barn_wide_or_scoped_to_program_group(self):
        iea = OrganizationGroup.objects.create(
            team=self.team,
            name="IEA Program",
            group_type=OrganizationGroup.GroupType.PROGRAM,
        )
        finance = Committee.objects.create(
            team=self.team,
            name="Finance Committee",
        )
        iea_events = Committee.objects.create(
            team=self.team,
            group=iea,
            name="Events Committee",
        )
        person = Person.objects.create(
            team=self.team,
            first_name="Morgan",
            last_name="Lee",
        )
        CommitteeMembership.objects.create(
            committee=finance,
            person=person,
            position=CommitteeMembership.Position.TREASURER,
            start_date=date(2026, 8, 1),
        )
        CommitteeMembership.objects.create(
            committee=iea_events,
            person=person,
            position=CommitteeMembership.Position.MEMBER,
            start_date=date(2026, 8, 1),
        )

        self.assertIsNone(finance.group)
        self.assertEqual(iea_events.group, iea)
        self.assertEqual(person.committee_memberships.count(), 2)

    def test_person_login_cannot_cross_organization_boundary(self):
        user = User.objects.create_user(username="crossorg", password="testpass")
        user.profile.team = self.other_team
        user.profile.save(update_fields=["team"])
        person = Person(
            team=self.team,
            user=user,
            first_name="Cross",
            last_name="Org",
        )

        with self.assertRaises(ValidationError):
            person.full_clean()
