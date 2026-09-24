from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from portal.forms import ActionItemForm
from portal.model_modules.people import Person, PersonRelationship
from portal.models import ActionItem, Team, UserProfile
from portal.view_modules.common import _visible_action_items


class V390ActionItemPersonNativeTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Person Native Actions")
        self.admin = User.objects.create_user(username="action-admin", password="test-pass")
        self.admin.profile.team = self.team
        self.admin.profile.role = UserProfile.Role.ADMIN
        self.admin.profile.save(update_fields=["team", "role"])
        self.parent_user = User.objects.create_user(username="action-parent", password="test-pass")
        self.parent_user.profile.team = self.team
        self.parent_user.profile.role = UserProfile.Role.PARENT
        self.parent_user.profile.save(update_fields=["team", "role"])
        self.parent = Person.objects.create(
            team=self.team, user=self.parent_user, first_name="Pat", last_name="Parent"
        )
        self.child = Person.objects.create(
            team=self.team, first_name="Casey", last_name="Participant"
        )
        PersonRelationship.objects.create(
            from_person=self.parent,
            to_person=self.child,
            relationship_type=PersonRelationship.RelationshipType.PARENT_GUARDIAN,
        )

    def test_action_item_can_target_person_without_legacy_rider(self):
        item = ActionItem.objects.create(
            team=self.team,
            title="Return paperwork",
            person=self.child,
            created_by=self.admin,
        )

        self.assertEqual(item.person, self.child)
        self.assertIsNone(item.rider_id)

    def test_action_item_form_uses_person_not_rider(self):
        form = ActionItemForm(team=self.team)

        self.assertIn("person", form.fields)
        self.assertNotIn("rider", form.fields)
        self.assertIn(self.child, form.fields["person"].queryset)

    def test_parent_can_see_child_person_action_without_legacy_rider(self):
        item = ActionItem.objects.create(
            team=self.team,
            title="Bring show forms",
            person=self.child,
            family_visible=True,
            created_by=self.admin,
        )

        visible = _visible_action_items(self.parent_user, self.team)

        self.assertIn(item, visible)

    def test_parent_cannot_see_unrelated_person_action(self):
        unrelated = Person.objects.create(
            team=self.team, first_name="Other", last_name="Participant"
        )
        item = ActionItem.objects.create(
            team=self.team,
            title="Private task",
            person=unrelated,
            family_visible=True,
            created_by=self.admin,
        )

        visible = _visible_action_items(self.parent_user, self.team)

        self.assertNotIn(item, visible)
