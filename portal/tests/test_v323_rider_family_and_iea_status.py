from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.people import LegacyPersonLink, OrganizationRoleAssignment, Person, PersonRelationship
from portal.models import Rider, RiderGuardian, Season, SeasonMembership, Team, UserProfile


class V323RiderFamilyAndIEAStatusTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
        self.admin = User.objects.create_user(username="rider-admin", password="pass12345")
        profile = self.admin.profile; profile.team = self.team; profile.role = UserProfile.Role.ADMIN; profile.save(update_fields=["team", "role"])
        self.client.force_login(self.admin)
        self.rider = Rider.objects.create(team=self.team, first_name="Jamie", last_name="Smith", grade=7)
        self.parent_person = Person.objects.create(team=self.team, first_name="Morgan", last_name="Smith", email="morgan@example.com", phone="555-0100")

    def _link_parent(self, relationship="Mother", primary=True):
        data = {"person": self.parent_person.pk, "relationship": relationship}
        if primary: data["primary_contact"] = "on"
        return self.client.post(reverse("rider_guardian_link", args=[self.rider.pk]), data)

    def test_link_existing_person_creates_legacy_and_canonical_parent_relationship(self):
        response = self._link_parent(); self.assertEqual(response.status_code, 302)
        rider_bridge = LegacyPersonLink.objects.get(rider=self.rider); parent_bridge = LegacyPersonLink.objects.get(person=self.parent_person)
        legacy_link = RiderGuardian.objects.get(rider=self.rider, guardian=parent_bridge.guardian)
        self.assertEqual(legacy_link.relationship, "Mother"); self.assertTrue(legacy_link.primary_contact)
        relationship = PersonRelationship.objects.get(from_person=self.parent_person, to_person=rider_bridge.person, relationship_type=PersonRelationship.RelationshipType.PARENT_GUARDIAN)
        self.assertEqual(relationship.label, "Mother"); self.assertTrue(relationship.primary_contact); self.assertTrue(relationship.active)
        self.assertTrue(OrganizationRoleAssignment.objects.filter(team=self.team, person=self.parent_person, role=OrganizationRoleAssignment.Role.PARENT_GUARDIAN, active=True).exists())

    def test_rider_profile_family_uses_canonical_people_relationship(self):
        self._link_parent(relationship="Mother", primary=True)
        relationship = PersonRelationship.objects.get(from_person=self.parent_person, relationship_type=PersonRelationship.RelationshipType.PARENT_GUARDIAN)
        legacy_link = RiderGuardian.objects.get(rider=self.rider)
        # Deliberately diverge the bridge. The profile must continue to display People.
        legacy_link.relationship = "Legacy label"; legacy_link.primary_contact = False; legacy_link.save(update_fields=["relationship", "primary_contact"])
        response = self.client.get(reverse("rider_detail", args=[self.rider.pk]))
        self.assertEqual(response.status_code, 200); self.assertContains(response, "FAMILY · PEOPLE")
        self.assertContains(response, self.parent_person.display_name); self.assertContains(response, "Mother · Primary contact")
        self.assertNotContains(response, "Legacy label")
        self.assertEqual(response.context["family_rows"][0]["relationship"], relationship)

    def test_unlink_ends_canonical_relationship_keeps_people_and_hides_family_row(self):
        self._link_parent(relationship="Guardian", primary=False)
        link = RiderGuardian.objects.get(rider=self.rider); rider_person = LegacyPersonLink.objects.get(rider=self.rider).person
        response = self.client.post(reverse("rider_guardian_unlink", args=[self.rider.pk, link.pk])); self.assertEqual(response.status_code, 302)
        self.assertTrue(Person.objects.filter(pk=self.parent_person.pk).exists())
        relationship = PersonRelationship.objects.get(from_person=self.parent_person, to_person=rider_person, relationship_type=PersonRelationship.RelationshipType.PARENT_GUARDIAN)
        self.assertFalse(relationship.active); self.assertIsNotNone(relationship.end_date)
        response = self.client.get(reverse("rider_detail", args=[self.rider.pk]))
        self.assertContains(response, "No active parent or guardian relationships in People.")
        self.assertNotContains(response, self.parent_person.email)

    def _seasons(self):
        old_season = Season.objects.create(team=self.team, name="2025-2026", start_date=date(2025, 8, 1), end_date=date(2026, 6, 30), is_active=False)
        active_season = Season.objects.create(team=self.team, name="2026-2027", start_date=date(2026, 8, 1), end_date=date(2027, 6, 30), is_active=True)
        return old_season, active_season

    def test_rider_card_uses_active_season_not_historical_membership(self):
        old_season, active_season = self._seasons(); SeasonMembership.objects.create(rider=self.rider, season=old_season, team_level=SeasonMembership.TeamLevel.FUTURES)
        response = self.client.get(reverse("rider_list")); self.assertEqual(response.status_code, 200); self.assertContains(response, "RIDER · NOT ON CURRENT IEA TEAM"); self.assertNotContains(response, "IEA TEAM · CURRENT")
        SeasonMembership.objects.create(rider=self.rider, season=active_season, team_level=SeasonMembership.TeamLevel.FUTURES)
        response = self.client.get(reverse("rider_list")); self.assertContains(response, "IEA TEAM · CURRENT"); self.assertContains(response, "Futures Team")

    def test_rider_profile_separates_current_membership_from_history(self):
        old_season, active_season = self._seasons(); SeasonMembership.objects.create(rider=self.rider, season=old_season, team_level=SeasonMembership.TeamLevel.UPPER)
        current = SeasonMembership.objects.create(rider=self.rider, season=active_season, team_level=SeasonMembership.TeamLevel.FUTURES)
        response = self.client.get(reverse("rider_detail", args=[self.rider.pk])); self.assertEqual(response.status_code, 200); self.assertEqual(response.context["current_membership"], current)
        self.assertEqual(list(response.context["historical_memberships"])[0].season, old_season); self.assertContains(response, "CURRENT IEA SEASON"); self.assertContains(response, "IEA TEAM · CURRENT"); self.assertContains(response, "Futures Team · Grade 7"); self.assertContains(response, "Previous IEA seasons"); self.assertContains(response, "2025-2026")

    def test_rider_profile_does_not_treat_historical_membership_as_current(self):
        old_season, active_season = self._seasons(); SeasonMembership.objects.create(rider=self.rider, season=old_season, team_level=SeasonMembership.TeamLevel.FUTURES)
        response = self.client.get(reverse("rider_detail", args=[self.rider.pk])); self.assertEqual(response.status_code, 200); self.assertIsNone(response.context["current_membership"])
        self.assertContains(response, "RIDER · NOT ON CURRENT IEA TEAM"); self.assertContains(response, f"Not assigned to {active_season.name}"); self.assertContains(response, "2025-2026"); self.assertNotContains(response, "IEA TEAM · CURRENT")
