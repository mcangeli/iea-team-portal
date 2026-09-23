from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from portal.model_modules.people import (
    OrganizationGroup,
    OrganizationGroupMembership,
    OrganizationRoleAssignment,
    Person,
)
from portal.models import Team


class V390OrganizationGroupMembershipTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
        self.other_team = Team.objects.create(name="Other Barn")
        self.lessons = OrganizationGroup.objects.create(
            team=self.team,
            name="Lesson Program",
            group_type=OrganizationGroup.GroupType.PROGRAM,
        )
        self.iea = OrganizationGroup.objects.create(
            team=self.team,
            name="IEA Program",
            group_type=OrganizationGroup.GroupType.PROGRAM,
        )
        self.person = Person.objects.create(
            team=self.team,
            first_name="Emma",
            last_name="Rider",
        )

    def test_one_person_can_participate_in_multiple_programs(self):
        OrganizationGroupMembership.objects.create(
            team=self.team,
            group=self.lessons,
            person=self.person,
        )
        OrganizationGroupMembership.objects.create(
            team=self.team,
            group=self.iea,
            person=self.person,
        )

        self.assertEqual(self.person.organization_group_memberships.count(), 2)

    def test_program_membership_does_not_require_login_account(self):
        membership = OrganizationGroupMembership(
            team=self.team,
            group=self.lessons,
            person=self.person,
        )
        membership.full_clean()
        membership.save()

        self.assertIsNone(self.person.user_id)

    def test_rider_role_and_program_membership_are_independent(self):
        OrganizationRoleAssignment.objects.create(
            team=self.team,
            person=self.person,
            role=OrganizationRoleAssignment.Role.RIDER,
        )
        membership = OrganizationGroupMembership.objects.create(
            team=self.team,
            group=self.lessons,
            person=self.person,
        )

        self.assertEqual(membership.person, self.person)
        self.assertTrue(
            self.person.role_assignments.filter(
                role=OrganizationRoleAssignment.Role.RIDER
            ).exists()
        )

    def test_membership_rejects_cross_organization_person(self):
        other_person = Person.objects.create(
            team=self.other_team,
            first_name="Other",
            last_name="Person",
        )
        membership = OrganizationGroupMembership(
            team=self.team,
            group=self.lessons,
            person=other_person,
        )

        with self.assertRaises(ValidationError):
            membership.full_clean()

    def test_membership_rejects_cross_organization_group(self):
        other_group = OrganizationGroup.objects.create(
            team=self.other_team,
            name="Other Program",
        )
        membership = OrganizationGroupMembership(
            team=self.team,
            group=other_group,
            person=self.person,
        )

        with self.assertRaises(ValidationError):
            membership.full_clean()

    def test_membership_rejects_end_before_start(self):
        today = timezone.localdate()
        membership = OrganizationGroupMembership(
            team=self.team,
            group=self.lessons,
            person=self.person,
            start_date=today,
            end_date=today - timedelta(days=1),
        )

        with self.assertRaises(ValidationError):
            membership.full_clean()

    def test_null_start_membership_is_unique_per_person_and_group(self):
        OrganizationGroupMembership.objects.create(
            team=self.team,
            group=self.lessons,
            person=self.person,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                OrganizationGroupMembership.objects.create(
                    team=self.team,
                    group=self.lessons,
                    person=self.person,
                )

    def test_distinct_membership_periods_preserve_history(self):
        today = timezone.localdate()
        first = OrganizationGroupMembership.objects.create(
            team=self.team,
            group=self.lessons,
            person=self.person,
            start_date=today - timedelta(days=365),
            end_date=today - timedelta(days=180),
            active=False,
            status=OrganizationGroupMembership.Status.ALUMNI,
        )
        second = OrganizationGroupMembership.objects.create(
            team=self.team,
            group=self.lessons,
            person=self.person,
            start_date=today,
        )

        self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(
            self.person.organization_group_memberships.filter(group=self.lessons).count(),
            2,
        )

    def test_role_label_is_descriptive_not_authorization(self):
        membership = OrganizationGroupMembership.objects.create(
            team=self.team,
            group=self.iea,
            person=self.person,
            role_label="Upper School Rider",
        )

        self.assertEqual(membership.role_label, "Upper School Rider")
        self.assertFalse(self.person.role_assignments.exists())
