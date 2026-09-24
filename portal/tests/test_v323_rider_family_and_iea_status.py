from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.people import LegacyPersonLink, OrganizationRoleAssignment, Person, PersonRelationship
from portal.models import GuardianContact, Rider, RiderGuardian, Season, SeasonMembership, Team, UserProfile


class V323RiderFamilyAndIEAStatusTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
        self.admin = User.objects.create_user(username="rider-admin", password="pass12345")
        profile = self.admin.profile; profile.team = self.team; profile.role = UserProfile.Role.ADMIN; profile.save(update_fields=["team", "role"])
        self.client.force_login(self.admin)
        self.rider = Rider.objects.create(team=self.team, first_name="Jamie", last_name="Smith", grade=7)
        self.parent_person = Person.objects.create(team=self.team, first_name="Morgan", last_name="Smith", email="morgan@example.com", phone="555-0100")

    def _link_parent(self, relationship="Mother", primary=True):
        data = {"person": f"person:{self.parent_person.pk}", "relationship": relationship}
        if primary: data["primary_contact"] = "on"
        return self.client.post(reverse("rider_guardian_link", args=[self.rider.pk]), data)

    def test_link_existing_person_creates_canonical_parent_relationship(self):
        response = self._link_parent(); self.assertEqual(response.status_code, 302)
        rider_bridge = LegacyPersonLink.objects.get(rider=self.rider)
        relationship = PersonRelationship.objects.get(from_person=self.parent_person, to_person=rider_bridge.person, relationship_type=PersonRelationship.RelationshipType.PARENT_GUARDIAN)
        self.assertEqual(relationship.label, "Mother"); self.assertTrue(relationship.primary_contact); self.assertTrue(relationship.active)
        self.assertFalse(LegacyPersonLink.objects.filter(person=self.parent_person).exists())

    def test_link_existing_login_migrates_to_person_without_duplicate_account(self):
        parent_user = User.objects.create_user(
            username="morgan.parent", password="pass12345", first_name="Morgan", last_name="Parent", email="parent@example.com"
        )
        profile = parent_user.profile; profile.team = self.team; profile.role = UserProfile.Role.PARENT; profile.save(update_fields=["team", "role"])
        before_users = User.objects.count(); before_people = Person.objects.count()
        response = self.client.post(reverse("rider_guardian_link", args=[self.rider.pk]), {
            "person": f"user:{parent_user.pk}", "relationship": "Father", "primary_contact": "on",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.objects.count(), before_users)
        self.assertEqual(Person.objects.count(), before_people + 2)  # rider Person + migrated parent Person
        parent_person = Person.objects.get(user=parent_user)
        rider_bridge = LegacyPersonLink.objects.get(rider=self.rider)
        self.assertFalse(LegacyPersonLink.objects.filter(person=parent_person).exists())
        self.assertFalse(self.rider.guardians.filter(pk=parent_user.pk).exists())
        relationship = PersonRelationship.objects.get(
            from_person=parent_person, to_person=rider_bridge.person,
            relationship_type=PersonRelationship.RelationshipType.PARENT_GUARDIAN,
        )
        self.assertEqual(relationship.label, "Father"); self.assertTrue(relationship.primary_contact)

    def test_existing_login_link_is_not_offered_again_after_linking(self):
        parent_user = User.objects.create_user(
            username="repeat.parent", password="pass12345", first_name="Repeat", last_name="Parent", email="repeat@example.com"
        )
        profile = parent_user.profile; profile.team = self.team; profile.role = UserProfile.Role.PARENT; profile.save(update_fields=["team", "role"])
        self.client.post(reverse("rider_guardian_link", args=[self.rider.pk]), {"person": f"user:{parent_user.pk}", "relationship": "Guardian"})
        response = self.client.get(reverse("rider_guardian_link", args=[self.rider.pk]))
        self.assertEqual(response.status_code, 200)
        values = {row["value"] for row in response.context["people"]}
        self.assertNotIn(f"user:{parent_user.pk}", values)
        self.assertNotIn(f"person:{parent_user.arena_person.pk}", values)

    def test_legacy_guardian_edit_route_redirects_to_person_relationship(self):
        guardian = GuardianContact.objects.create(
            team=self.team,
            first_name="Morgan",
            last_name="Legacy",
            email="legacy@example.com",
        )
        link = RiderGuardian.objects.create(
            rider=self.rider,
            guardian=guardian,
            relationship="Guardian",
            primary_contact=True,
        )

        response = self.client.get(
            reverse("rider_guardian_edit", args=[self.rider.pk, guardian.pk])
        )

        rider_person = LegacyPersonLink.objects.get(rider=self.rider).person
        guardian_person = LegacyPersonLink.objects.get(guardian=guardian).person
        relationship = PersonRelationship.objects.get(
            from_person=guardian_person,
            to_person=rider_person,
            relationship_type=PersonRelationship.RelationshipType.PARENT_GUARDIAN,
        )
        self.assertRedirects(
            response,
            reverse(
                "person_relationship_edit",
                args=[guardian_person.pk, relationship.pk],
            ),
        )
        link.refresh_from_db()

    def test_legacy_guardian_unlink_ends_canonical_relationship_and_keeps_people(self):
        guardian = GuardianContact.objects.create(
            team=self.team,
            first_name="Morgan",
            last_name="Unlink",
            email="unlink@example.com",
        )
        link = RiderGuardian.objects.create(
            rider=self.rider,
            guardian=guardian,
            relationship="Guardian",
            primary_contact=True,
        )
        from portal.people_compat import sync_rider_guardian_link
        relationship = sync_rider_guardian_link(link)
        rider_person = relationship.to_person
        guardian_person = relationship.from_person

        response = self.client.post(
            reverse("rider_guardian_unlink", args=[self.rider.pk, link.pk])
        )

        self.assertRedirects(response, reverse("rider_detail", args=[self.rider.pk]))
        relationship.refresh_from_db()
        self.assertFalse(relationship.active)
        self.assertIsNotNone(relationship.end_date)
        self.assertFalse(RiderGuardian.objects.filter(pk=link.pk).exists())
        self.assertTrue(Person.objects.filter(pk=rider_person.pk).exists())
        self.assertTrue(Person.objects.filter(pk=guardian_person.pk).exists())

    def test_rider_profile_family_uses_canonical_people_relationship(self):
        self._link_parent(relationship="Mother", primary=True)
        relationship = PersonRelationship.objects.get(from_person=self.parent_person, relationship_type=PersonRelationship.RelationshipType.PARENT_GUARDIAN)
        response = self.client.get(reverse("rider_detail", args=[self.rider.pk]))
        self.assertEqual(response.status_code, 200); self.assertContains(response, "FAMILY · PEOPLE")
        self.assertContains(response, self.parent_person.display_name); self.assertContains(response, "Mother · Primary contact")
        self.assertEqual(response.context["family_rows"][0]["relationship"], relationship)
        self.assertIsNone(response.context["family_rows"][0]["legacy_link"])

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
