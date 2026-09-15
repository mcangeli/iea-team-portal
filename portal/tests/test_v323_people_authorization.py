from django.contrib.auth.models import User
from django.test import TestCase

from portal.model_modules.people import Person, PersonRelationship
from portal.models import Team, UserProfile
from portal.people_services import can_view_private_person, has_active_parent_relationship


class V323PeopleAuthorizationTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
        self.other_team = Team.objects.create(name="Other Barn")

        self.parent_user = User.objects.create_user(username="parent-auth", password="pass12345")
        parent_profile = self.parent_user.profile
        parent_profile.team = self.team
        parent_profile.role = UserProfile.Role.PARENT
        parent_profile.save(update_fields=["team", "role"])
        self.parent = Person.objects.create(
            team=self.team, user=self.parent_user, first_name="Morgan", last_name="Smith"
        )

        self.rider_user = User.objects.create_user(username="rider-auth", password="pass12345")
        rider_profile = self.rider_user.profile
        rider_profile.team = self.team
        rider_profile.role = UserProfile.Role.RIDER
        rider_profile.save(update_fields=["team", "role"])
        self.rider = Person.objects.create(
            team=self.team, user=self.rider_user, first_name="Jamie", last_name="Smith"
        )

        self.unrelated = Person.objects.create(
            team=self.team, first_name="Taylor", last_name="Jones"
        )

    def _relationship(self, **overrides):
        values = {
            "from_person": self.parent,
            "to_person": self.rider,
            "relationship_type": PersonRelationship.RelationshipType.PARENT_GUARDIAN,
            "active": True,
        }
        values.update(overrides)
        return PersonRelationship.objects.create(**values)

    def test_parent_can_view_related_person_through_canonical_relationship(self):
        self._relationship()
        self.assertTrue(has_active_parent_relationship(self.parent, self.rider))
        self.assertTrue(can_view_private_person(self.parent_user, self.rider))

    def test_parent_cannot_view_unrelated_person(self):
        self._relationship()
        self.assertFalse(can_view_private_person(self.parent_user, self.unrelated))

    def test_inactive_relationship_does_not_grant_access(self):
        self._relationship(active=False)
        self.assertFalse(has_active_parent_relationship(self.parent, self.rider))
        self.assertFalse(can_view_private_person(self.parent_user, self.rider))

    def test_ended_relationship_does_not_grant_access(self):
        from datetime import date
        self._relationship(end_date=date.today())
        self.assertFalse(has_active_parent_relationship(self.parent, self.rider))
        self.assertFalse(can_view_private_person(self.parent_user, self.rider))

    def test_person_can_view_own_private_profile(self):
        self.assertTrue(can_view_private_person(self.rider_user, self.rider))

    def test_manager_can_view_private_person_without_family_relationship(self):
        admin = User.objects.create_user(username="people-admin", password="pass12345")
        profile = admin.profile
        profile.team = self.team
        profile.role = UserProfile.Role.ADMIN
        profile.save(update_fields=["team", "role"])
        self.assertTrue(can_view_private_person(admin, self.unrelated))

    def test_relationship_is_directional(self):
        self._relationship()
        self.assertFalse(has_active_parent_relationship(self.rider, self.parent))
        self.assertFalse(can_view_private_person(self.rider_user, self.parent))

    def test_relationship_cannot_cross_organization_boundary(self):
        outsider = Person.objects.create(team=self.other_team, first_name="Outside", last_name="Person")
        self.assertFalse(has_active_parent_relationship(self.parent, outsider))
