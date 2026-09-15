from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase

from portal.model_modules.people import LegacyPersonLink, Person, PersonRelationship
from portal.models import GuardianContact, Rider, RiderGuardian, Season, SeasonMembership, Team, UserProfile
from portal.people_services import (
    can_view_family_account, can_view_private_person, can_view_private_rider,
    has_active_parent_relationship, personal_riders_for_user, visible_riders_for_user,
)
from portal.view_modules.common import _can_view_family_account, _personal_riders, _visible_riders


class V323PeopleAuthorizationTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
        self.other_team = Team.objects.create(name="Other Barn")
        self.parent_user = User.objects.create_user(username="parent-auth", password="pass12345")
        p = self.parent_user.profile; p.team = self.team; p.role = UserProfile.Role.PARENT; p.save(update_fields=["team", "role"])
        self.parent = Person.objects.create(team=self.team, user=self.parent_user, first_name="Morgan", last_name="Smith")
        self.rider_user = User.objects.create_user(username="rider-auth", password="pass12345")
        p = self.rider_user.profile; p.team = self.team; p.role = UserProfile.Role.RIDER; p.save(update_fields=["team", "role"])
        self.rider = Person.objects.create(team=self.team, user=self.rider_user, first_name="Jamie", last_name="Smith")
        self.unrelated = Person.objects.create(team=self.team, first_name="Taylor", last_name="Jones")

    def _relationship(self, **overrides):
        values = {"from_person": self.parent, "to_person": self.rider,
                  "relationship_type": PersonRelationship.RelationshipType.PARENT_GUARDIAN, "active": True}
        values.update(overrides); return PersonRelationship.objects.create(**values)

    def _legacy_rider_bridge(self):
        rider = Rider.objects.create(team=self.team, first_name="Jamie", last_name="Smith", grade=7)
        LegacyPersonLink.objects.create(person=self.rider, rider=rider); return rider

    def _season(self):
        return Season.objects.create(team=self.team, name="2026-27", start_date=date(2026, 8, 1), end_date=date(2027, 7, 31))

    def test_parent_can_view_related_person_through_canonical_relationship(self):
        self._relationship(); self.assertTrue(has_active_parent_relationship(self.parent, self.rider)); self.assertTrue(can_view_private_person(self.parent_user, self.rider))

    def test_parent_cannot_view_unrelated_person(self):
        self._relationship(); self.assertFalse(can_view_private_person(self.parent_user, self.unrelated))

    def test_inactive_relationship_does_not_grant_access(self):
        self._relationship(active=False); self.assertFalse(has_active_parent_relationship(self.parent, self.rider)); self.assertFalse(can_view_private_person(self.parent_user, self.rider))

    def test_ended_relationship_does_not_grant_access(self):
        self._relationship(end_date=date.today()); self.assertFalse(has_active_parent_relationship(self.parent, self.rider)); self.assertFalse(can_view_private_person(self.parent_user, self.rider))

    def test_future_relationship_does_not_grant_access_early(self):
        self._relationship(start_date=date.today() + timedelta(days=1)); self.assertFalse(has_active_parent_relationship(self.parent, self.rider)); self.assertFalse(can_view_private_person(self.parent_user, self.rider))

    def test_relationship_with_future_end_date_remains_active(self):
        self._relationship(end_date=date.today() + timedelta(days=1)); self.assertTrue(has_active_parent_relationship(self.parent, self.rider)); self.assertTrue(can_view_private_person(self.parent_user, self.rider))

    def test_relationship_starting_today_is_active(self):
        self._relationship(start_date=date.today()); self.assertTrue(has_active_parent_relationship(self.parent, self.rider)); self.assertTrue(can_view_private_person(self.parent_user, self.rider))

    def test_person_can_view_own_private_profile(self): self.assertTrue(can_view_private_person(self.rider_user, self.rider))

    def test_manager_can_view_private_person_without_family_relationship(self):
        admin = User.objects.create_user(username="people-admin", password="pass12345"); p = admin.profile; p.team = self.team; p.role = UserProfile.Role.ADMIN; p.save(update_fields=["team", "role"]); self.assertTrue(can_view_private_person(admin, self.unrelated))

    def test_relationship_is_directional(self):
        self._relationship(); self.assertFalse(has_active_parent_relationship(self.rider, self.parent)); self.assertFalse(can_view_private_person(self.rider_user, self.parent))

    def test_relationship_cannot_cross_organization_boundary(self):
        outsider = Person.objects.create(team=self.other_team, first_name="Outside", last_name="Person"); self.assertFalse(has_active_parent_relationship(self.parent, outsider))

    def test_canonical_only_parent_relationship_grants_private_rider_access(self):
        rider = self._legacy_rider_bridge(); self._relationship(); self.assertFalse(RiderGuardian.objects.filter(rider=rider).exists()); self.assertTrue(can_view_private_rider(self.parent_user, rider)); self.assertEqual(list(personal_riders_for_user(self.parent_user, self.team)), [rider])

    def test_ended_canonical_relationship_removes_rider_access_without_legacy_fallback(self):
        rider = self._legacy_rider_bridge(); self._relationship(end_date=date.today()); self.assertFalse(can_view_private_rider(self.parent_user, rider)); self.assertFalse(personal_riders_for_user(self.parent_user, self.team).filter(pk=rider.pk).exists())

    def test_legacy_only_guardian_relationship_remains_authorized_as_compatibility_fallback(self):
        rider = self._legacy_rider_bridge(); guardian = GuardianContact.objects.create(team=self.team, user=self.parent_user, first_name="Morgan", last_name="Smith", email="morgan@example.com"); RiderGuardian.objects.create(rider=rider, guardian=guardian, relationship="Mother"); self.assertTrue(can_view_private_rider(self.parent_user, rider)); self.assertTrue(personal_riders_for_user(self.parent_user, self.team).filter(pk=rider.pk).exists())

    def test_shared_operational_visibility_uses_canonical_family_relationship(self):
        rider = self._legacy_rider_bridge(); self._relationship(); self.assertEqual(list(visible_riders_for_user(self.parent_user, self.team)), [rider]); self.assertEqual(list(_personal_riders(self.parent_user, self.team)), [rider]); self.assertEqual(list(_visible_riders(self.parent_user, self.team)), [rider])

    def test_shared_operational_visibility_excludes_unrelated_rider(self):
        related = self._legacy_rider_bridge(); person = Person.objects.create(team=self.team, first_name="Alex", last_name="Other"); rider = Rider.objects.create(team=self.team, first_name="Alex", last_name="Other", grade=8); LegacyPersonLink.objects.create(person=person, rider=rider); self._relationship(); self.assertEqual(list(_visible_riders(self.parent_user, self.team)), [related])

    def test_family_account_uses_same_canonical_family_boundary(self):
        rider = self._legacy_rider_bridge(); self._relationship(); membership = SeasonMembership.objects.create(season=self._season(), rider=rider, team_level=SeasonMembership.TeamLevel.FUTURES); self.assertTrue(can_view_family_account(self.parent_user, membership)); self.assertTrue(_can_view_family_account(self.parent_user, membership))

    def test_ended_canonical_relationship_removes_family_account_access(self):
        rider = self._legacy_rider_bridge(); self._relationship(end_date=date.today()); membership = SeasonMembership.objects.create(season=self._season(), rider=rider, team_level=SeasonMembership.TeamLevel.FUTURES); self.assertFalse(can_view_family_account(self.parent_user, membership)); self.assertFalse(_can_view_family_account(self.parent_user, membership))

    def test_canonical_rider_login_can_see_self_without_legacy_user_link(self):
        rider = self._legacy_rider_bridge()
        self.assertIsNone(rider.user_id)
        self.assertTrue(can_view_private_rider(self.rider_user, rider))
        self.assertEqual(list(visible_riders_for_user(self.rider_user, self.team)), [rider])
        self.assertEqual(list(_visible_riders(self.rider_user, self.team)), [rider])

    def test_coach_private_access_does_not_grant_family_finance_access(self):
        rider = self._legacy_rider_bridge(); membership = SeasonMembership.objects.create(season=self._season(), rider=rider, team_level=SeasonMembership.TeamLevel.FUTURES)
        coach = User.objects.create_user(username="coach-auth", password="pass12345"); p = coach.profile; p.team = self.team; p.role = UserProfile.Role.COACH; p.save(update_fields=["team", "role"])
        self.assertTrue(can_view_private_rider(coach, rider))
        self.assertFalse(can_view_family_account(coach, membership))
        self.assertFalse(_can_view_family_account(coach, membership))
