from django.db import IntegrityError, transaction
from django.test import TestCase

from portal.model_modules.barn_participation import HorsePersonRelationship
from portal.model_modules.horses import Horse
from portal.model_modules.people import (
    Committee,
    CommitteeMembership,
    OrganizationRoleAssignment,
    Person,
)
from portal.models import Team


class V323NullSafeUniquenessTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
        self.person = Person.objects.create(team=self.team, first_name="Jamie", last_name="Smith")
        self.horse = Horse.objects.create(team=self.team, name="Jasper")

    def test_null_start_role_assignment_cannot_duplicate(self):
        OrganizationRoleAssignment.objects.create(
            team=self.team,
            person=self.person,
            role=OrganizationRoleAssignment.Role.WORKING_STUDENT,
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            OrganizationRoleAssignment.objects.create(
                team=self.team,
                person=self.person,
                role=OrganizationRoleAssignment.Role.WORKING_STUDENT,
            )

    def test_barnwide_committee_name_cannot_duplicate(self):
        Committee.objects.create(team=self.team, name="Finance Committee")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Committee.objects.create(team=self.team, name="Finance Committee")

    def test_null_start_committee_membership_cannot_duplicate(self):
        committee = Committee.objects.create(team=self.team, name="Events Committee")
        CommitteeMembership.objects.create(
            committee=committee,
            person=self.person,
            position=CommitteeMembership.Position.MEMBER,
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            CommitteeMembership.objects.create(
                committee=committee,
                person=self.person,
                position=CommitteeMembership.Position.MEMBER,
            )

    def test_null_start_horse_relationship_cannot_duplicate(self):
        HorsePersonRelationship.objects.create(
            team=self.team,
            horse=self.horse,
            person=self.person,
            relationship_type=HorsePersonRelationship.RelationshipType.TRAINER,
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            HorsePersonRelationship.objects.create(
                team=self.team,
                horse=self.horse,
                person=self.person,
                relationship_type=HorsePersonRelationship.RelationshipType.TRAINER,
            )
