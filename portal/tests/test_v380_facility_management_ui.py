from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.facilities import Facility, FacilitySpace
from portal.models import AuditEvent, Team, UserProfile


class FacilityManagementUITests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Foundation Barn")
        self.other_team = Team.objects.create(name="Other Barn")
        self.admin = User.objects.create_user(username="facility-admin", password="pass12345")
        self.admin.profile.team = self.team
        self.admin.profile.role = UserProfile.Role.ADMIN
        self.admin.profile.save(update_fields=["team", "role"])
        self.parent = User.objects.create_user(username="facility-parent", password="pass12345")
        self.parent.profile.team = self.team
        self.parent.profile.role = UserProfile.Role.PARENT
        self.parent.profile.save(update_fields=["team", "role"])
        self.facility = Facility.objects.create(team=self.team, name="Main Farm")
        self.other_facility = Facility.objects.create(team=self.other_team, name="Other Farm")

    def test_facility_list_is_scoped_to_users_organization(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("facility_list"))
        self.assertContains(response, "Main Farm")
        self.assertNotContains(response, "Other Farm")

    def test_facility_detail_rejects_cross_organization_lookup(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("facility_detail", args=[self.other_facility.pk]))
        self.assertEqual(response.status_code, 404)

    def test_admin_can_create_facility(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("facility_create"), {
            "name": "North Farm", "address": "100 Barn Lane", "active": "on", "notes": "",
        })
        created = Facility.objects.get(team=self.team, name="North Farm")
        self.assertRedirects(response, reverse("facility_detail", args=[created.pk]))

    def test_non_manager_cannot_create_or_edit_facility(self):
        self.client.force_login(self.parent)
        self.assertEqual(self.client.get(reverse("facility_create")).status_code, 403)
        self.assertEqual(self.client.get(reverse("facility_edit", args=[self.facility.pk])).status_code, 403)

    def test_admin_can_create_nested_space(self):
        barn = FacilitySpace.objects.create(
            facility=self.facility, name="Main Barn", space_type=FacilitySpace.SpaceType.BARN
        )
        self.client.force_login(self.admin)
        response = self.client.post(reverse("facility_space_create", args=[self.facility.pk]), {
            "parent": barn.pk, "name": "Stall 1", "space_type": FacilitySpace.SpaceType.STALL,
            "housing_capable": "on", "active": "on", "notes": "",
        })
        space = FacilitySpace.objects.get(facility=self.facility, name="Stall 1")
        self.assertEqual(space.parent, barn)
        self.assertTrue(space.housing_capable)
        self.assertRedirects(response, reverse("facility_detail", args=[self.facility.pk]))

    def test_parent_choices_cannot_cross_organization_boundary(self):
        other_barn = FacilitySpace.objects.create(
            facility=self.other_facility, name="Other Barn", space_type=FacilitySpace.SpaceType.BARN
        )
        self.client.force_login(self.admin)
        response = self.client.post(reverse("facility_space_create", args=[self.facility.pk]), {
            "parent": other_barn.pk, "name": "Bad Stall", "space_type": FacilitySpace.SpaceType.STALL,
            "housing_capable": "on", "active": "on", "notes": "",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(FacilitySpace.objects.filter(facility=self.facility, name="Bad Stall").exists())

    def test_cross_organization_space_edit_is_not_found(self):
        other_space = FacilitySpace.objects.create(
            facility=self.other_facility, name="Other Arena", space_type=FacilitySpace.SpaceType.ARENA
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse("facility_space_edit", args=[other_space.pk]))
        self.assertEqual(response.status_code, 404)


    def test_facility_detail_builds_parent_child_hierarchy(self):
        barn = FacilitySpace.objects.create(
            facility=self.facility, name="Main Barn", space_type=FacilitySpace.SpaceType.BARN
        )
        stall = FacilitySpace.objects.create(
            facility=self.facility, parent=barn, name="Stall 1",
            space_type=FacilitySpace.SpaceType.STALL, housing_capable=True
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse("facility_detail", args=[self.facility.pk]))
        tree = response.context["space_tree"]
        self.assertEqual(len(tree), 1)
        self.assertEqual(tree[0]["space"], barn)
        self.assertEqual(tree[0]["children"][0]["space"], stall)


    def test_duplicate_facility_name_returns_form_error(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("facility_create"), {
            "name": self.facility.name, "address": "", "active": "on", "notes": "",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Facility.objects.filter(team=self.team, name=self.facility.name).count(), 1)
        self.assertTrue(response.context["form"].errors)

    def test_facility_create_and_update_are_audited(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("facility_create"), {
            "name": "Audited Farm", "address": "", "active": "on", "notes": "",
        })
        self.assertEqual(response.status_code, 302)
        facility = Facility.objects.get(team=self.team, name="Audited Farm")
        self.assertTrue(AuditEvent.objects.filter(team=self.team, object_id=str(facility.pk), action=AuditEvent.Action.CREATED).exists())
        response = self.client.post(reverse("facility_edit", args=[facility.pk]), {
            "name": "Audited Farm Updated", "address": "", "active": "on", "notes": "",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(AuditEvent.objects.filter(team=self.team, object_id=str(facility.pk), action=AuditEvent.Action.UPDATED).exists())
