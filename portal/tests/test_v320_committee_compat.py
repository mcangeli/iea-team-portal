from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase

from portal.model_modules.people import Committee, CommitteeMembership, OrganizationGroup, Person
from portal.models import CommitteeAssignment, Season, Team, UserProfile


class V320CommitteeCompatibilityTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
        self.season = Season.objects.create(
            team=self.team,
            name="2026-2027",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 6, 30),
            is_active=True,
        )
        self.user = User.objects.create_user(
            username="committee-v320",
            password="pass12345",
            first_name="Jamie",
            last_name="Smith",
        )
        profile = UserProfile.objects.get(user=self.user)
        profile.team = self.team
        profile.role = UserProfile.Role.PARENT
        profile.save(update_fields=["team", "role"])
        self.person = Person.objects.create(
            team=self.team,
            user=self.user,
            first_name="Jamie",
            last_name="Smith",
        )

    def test_parent_assignment_mirrors_to_iea_committee_chair(self):
        assignment = CommitteeAssignment.objects.create(
            team=self.team,
            season=self.season,
            user=self.user,
            role=CommitteeAssignment.Role.FUTURES_PARENT,
        )
        membership = CommitteeMembership.objects.get(legacy_committee_assignment=assignment)
        self.assertEqual(membership.person, self.person)
        self.assertEqual(membership.position, CommitteeMembership.Position.CHAIR)
        self.assertEqual(membership.committee.name, "Futures Team Parent Committee")
        self.assertEqual(membership.committee.group.name, "IEA Program")
        self.assertEqual(membership.start_date, self.season.start_date)
        self.assertEqual(membership.end_date, self.season.end_date)
        self.assertTrue(membership.active)

    def test_treasurer_maps_to_organization_finance_committee(self):
        assignment = CommitteeAssignment.objects.create(
            team=self.team,
            season=self.season,
            user=self.user,
            role=CommitteeAssignment.Role.TREASURER,
        )
        membership = CommitteeMembership.objects.get(legacy_committee_assignment=assignment)
        self.assertEqual(membership.position, CommitteeMembership.Position.TREASURER)
        self.assertEqual(membership.committee.name, "Finance Committee")
        self.assertIsNone(membership.committee.group)

    def test_legacy_deactivation_updates_mirrored_membership(self):
        assignment = CommitteeAssignment.objects.create(
            team=self.team,
            season=self.season,
            user=self.user,
            role=CommitteeAssignment.Role.POINTS_SECRETARY,
        )
        assignment.active = False
        assignment.save(update_fields=["active"])
        membership = CommitteeMembership.objects.get(legacy_committee_assignment=assignment)
        self.assertFalse(membership.active)
        self.assertEqual(membership.position, CommitteeMembership.Position.SECRETARY)
        self.assertEqual(membership.committee.name, "IEA Points & Records")

    def test_deleting_legacy_assignment_only_removes_its_mirror(self):
        manual_committee = Committee.objects.create(team=self.team, name="Events Committee")
        manual_membership = CommitteeMembership.objects.create(
            committee=manual_committee,
            person=self.person,
            position=CommitteeMembership.Position.MEMBER,
        )
        assignment = CommitteeAssignment.objects.create(
            team=self.team,
            season=self.season,
            user=self.user,
            role=CommitteeAssignment.Role.UPPER_PARENT,
        )
        mirrored_id = CommitteeMembership.objects.get(legacy_committee_assignment=assignment).pk
        assignment.delete()
        self.assertFalse(CommitteeMembership.objects.filter(pk=mirrored_id).exists())
        self.assertTrue(CommitteeMembership.objects.filter(pk=manual_membership.pk).exists())
        self.assertTrue(OrganizationGroup.objects.filter(team=self.team, name="IEA Program").exists())
