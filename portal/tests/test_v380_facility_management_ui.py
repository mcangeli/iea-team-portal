from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from portal.model_modules.facilities import Facility, FacilitySpace, ResourceReservation
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


    def test_facility_detail_shows_only_top_level_spaces(self):
        barn = FacilitySpace.objects.create(
            facility=self.facility, name="Main Barn", space_type=FacilitySpace.SpaceType.BARN
        )
        FacilitySpace.objects.create(
            facility=self.facility, parent=barn, name="Stall 1",
            space_type=FacilitySpace.SpaceType.STALL, housing_capable=True
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse("facility_detail", args=[self.facility.pk]))
        self.assertContains(response, "Main Barn")
        self.assertContains(response, "1 stall")
        self.assertNotContains(response, "Stall 1")

    def test_space_detail_groups_immediate_resources(self):
        barn = FacilitySpace.objects.create(
            facility=self.facility, name="Main Barn", space_type=FacilitySpace.SpaceType.BARN
        )
        stall = FacilitySpace.objects.create(
            facility=self.facility, parent=barn, name="Stall 12",
            space_type=FacilitySpace.SpaceType.STALL, housing_capable=True
        )
        storage = FacilitySpace.objects.create(
            facility=self.facility, parent=barn, name="Feed Storage",
            space_type=FacilitySpace.SpaceType.STORAGE, inventory_storage_capable=True
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse("facility_space_detail", args=[barn.pk]))
        self.assertContains(response, "Stalls")
        self.assertContains(response, stall.name)
        self.assertContains(response, "Storage")
        self.assertContains(response, storage.name)

    def test_space_detail_rejects_cross_organization_lookup(self):
        other_space = FacilitySpace.objects.create(
            facility=self.other_facility, name="Other Barn", space_type=FacilitySpace.SpaceType.BARN
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse("facility_space_detail", args=[other_space.pk]))
        self.assertEqual(response.status_code, 404)

    def test_large_stall_inventory_does_not_expand_on_facility_page(self):
        barn = FacilitySpace.objects.create(
            facility=self.facility, name="Large Barn", space_type=FacilitySpace.SpaceType.BARN
        )
        for number in range(1, 51):
            FacilitySpace.objects.create(
                facility=self.facility, parent=barn, name=f"Scale Stall {number}",
                space_type=FacilitySpace.SpaceType.STALL, housing_capable=True,
            )
        self.client.force_login(self.admin)
        response = self.client.get(reverse("facility_detail", args=[self.facility.pk]))
        self.assertContains(response, "Large Barn")
        self.assertContains(response, "50 stalls")
        self.assertNotContains(response, "Scale Stall 1")
        barn_response = self.client.get(reverse("facility_space_detail", args=[barn.pk]))
        self.assertContains(barn_response, "Scale Stall 1")
        self.assertContains(barn_response, "Scale Stall 50")


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
        self.assertTrue(AuditEvent.objects.filter(team=self.team, entity_id=facility.pk, action=AuditEvent.Action.CREATED).exists())
        response = self.client.post(reverse("facility_edit", args=[facility.pk]), {
            "name": "Audited Farm Updated", "address": "", "active": "on", "notes": "",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(AuditEvent.objects.filter(team=self.team, entity_id=facility.pk, action=AuditEvent.Action.UPDATED).exists())


    def test_manager_can_create_resource_reservation(self):
        ring = FacilitySpace.objects.create(
            facility=self.facility, name="Indoor Ring",
            space_type=FacilitySpace.SpaceType.ARENA, reservable=True,
        )
        starts = timezone.now() + timedelta(days=1)
        ends = starts + timedelta(hours=1)
        self.client.force_login(self.admin)
        response = self.client.post(reverse("resource_reservation_create", args=[ring.pk]), {
            "title": "Private lesson",
            "starts_at": starts.strftime("%Y-%m-%dT%H:%M"),
            "ends_at": ends.strftime("%Y-%m-%dT%H:%M"),
            "notes": "",
        })
        reservation = ResourceReservation.objects.get(space=ring, title="Private lesson")
        self.assertRedirects(response, reverse("facility_space_detail", args=[ring.pk]))
        self.assertTrue(AuditEvent.objects.filter(
            team=self.team, entity_id=reservation.pk, action=AuditEvent.Action.CREATED
        ).exists())

    def test_overlapping_reservation_returns_form_error(self):
        ring = FacilitySpace.objects.create(
            facility=self.facility, name="Outdoor Ring",
            space_type=FacilitySpace.SpaceType.ARENA, reservable=True,
        )
        starts = timezone.now() + timedelta(days=1)
        ResourceReservation.objects.create(
            space=ring, title="Existing", starts_at=starts, ends_at=starts + timedelta(hours=1)
        )
        self.client.force_login(self.admin)
        response = self.client.post(reverse("resource_reservation_create", args=[ring.pk]), {
            "title": "Conflict",
            "starts_at": timezone.localtime(starts + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M"),
            "ends_at": timezone.localtime(starts + timedelta(hours=1, minutes=30)).strftime("%Y-%m-%dT%H:%M"),
            "notes": "",
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertFalse(ResourceReservation.objects.filter(space=ring, title="Conflict").exists())

    def test_non_manager_cannot_manage_reservations(self):
        ring = FacilitySpace.objects.create(
            facility=self.facility, name="Schooling Ring",
            space_type=FacilitySpace.SpaceType.ARENA, reservable=True,
        )
        self.client.force_login(self.parent)
        self.assertEqual(
            self.client.get(reverse("resource_reservation_create", args=[ring.pk])).status_code, 403
        )

    def test_resource_page_shows_upcoming_reservations(self):
        ring = FacilitySpace.objects.create(
            facility=self.facility, name="Competition Ring",
            space_type=FacilitySpace.SpaceType.ARENA, reservable=True,
        )
        starts = timezone.now() + timedelta(days=1)
        ResourceReservation.objects.create(
            space=ring, title="Arena maintenance",
            starts_at=starts, ends_at=starts + timedelta(hours=2),
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse("facility_space_detail", args=[ring.pk]))
        self.assertContains(response, "Upcoming reservations")
        self.assertContains(response, "Arena maintenance")
        self.assertContains(response, "Reserve resource")


    def test_cancelled_reservation_is_preserved_in_history_and_frees_slot(self):
        ring = FacilitySpace.objects.create(
            facility=self.facility, name="History Ring",
            space_type=FacilitySpace.SpaceType.ARENA, reservable=True,
        )
        starts = timezone.now() + timedelta(days=1)
        reservation = ResourceReservation.objects.create(
            space=ring, title="Cancelled lesson",
            starts_at=starts, ends_at=starts + timedelta(hours=1),
        )
        self.client.force_login(self.admin)
        response = self.client.post(reverse("resource_reservation_cancel", args=[reservation.pk]))
        self.assertRedirects(response, reverse("facility_space_detail", args=[ring.pk]))
        reservation.refresh_from_db()
        self.assertIsNotNone(reservation.cancelled_at)

        replacement = ResourceReservation(
            space=ring, title="Replacement lesson",
            starts_at=starts, ends_at=starts + timedelta(hours=1),
        )
        replacement.full_clean()

        detail = self.client.get(reverse("facility_space_detail", args=[ring.pk]))
        self.assertContains(detail, "Reservation history")
        self.assertContains(detail, "Cancelled lesson")
        self.assertContains(detail, "Cancelled")

    def test_completed_reservation_appears_in_history(self):
        ring = FacilitySpace.objects.create(
            facility=self.facility, name="Past Ring",
            space_type=FacilitySpace.SpaceType.ARENA, reservable=True,
        )
        ends = timezone.now() - timedelta(hours=1)
        ResourceReservation.objects.create(
            space=ring, title="Morning schooling",
            starts_at=ends - timedelta(hours=1), ends_at=ends,
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse("facility_space_detail", args=[ring.pk]))
        self.assertContains(response, "Reservation history")
        self.assertContains(response, "Morning schooling")


    def test_nested_space_create_honors_parent_navigation_context(self):
        barn = FacilitySpace.objects.create(
            facility=self.facility, name="Navigation Barn", space_type=FacilitySpace.SpaceType.BARN
        )
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("facility_space_create", args=[self.facility.pk]), {"parent": barn.pk}
        )
        self.assertEqual(response.context["form"].initial["parent"], barn)
        self.assertContains(response, reverse("facility_space_detail", args=[barn.pk]))

        response = self.client.post(reverse("facility_space_create", args=[self.facility.pk]), {
            "parent": barn.pk, "name": "Navigation Stall", "space_type": FacilitySpace.SpaceType.STALL,
            "housing_capable": "on", "active": "on", "notes": "",
        })
        self.assertRedirects(response, reverse("facility_space_detail", args=[barn.pk]))

    def test_space_edit_returns_to_edited_resource(self):
        space = FacilitySpace.objects.create(
            facility=self.facility, name="Navigation Storage",
            space_type=FacilitySpace.SpaceType.STORAGE, inventory_storage_capable=True,
        )
        self.client.force_login(self.admin)
        response = self.client.post(reverse("facility_space_edit", args=[space.pk]), {
            "parent": "", "name": "Navigation Storage Updated",
            "space_type": FacilitySpace.SpaceType.STORAGE,
            "inventory_storage_capable": "on", "active": "on", "notes": "",
        })
        self.assertRedirects(response, reverse("facility_space_detail", args=[space.pk]))
