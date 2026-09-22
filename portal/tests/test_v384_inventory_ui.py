from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.models import Team, UserProfile
from portal.model_modules.facilities import Facility, FacilitySpace
from portal.model_modules.inventory import InventoryCategory, InventoryItem, InventoryStock


class InventoryUITests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Inventory UI Barn")
        self.other_team = Team.objects.create(name="Other Barn")
        self.admin = User.objects.create_user(username="inventory-admin", password="pass12345")
        self.admin.profile.team = self.team
        self.admin.profile.role = UserProfile.Role.ADMIN
        self.admin.profile.save(update_fields=["team", "role"])
        self.parent = User.objects.create_user(username="inventory-parent", password="pass12345")
        self.parent.profile.team = self.team
        self.parent.profile.role = UserProfile.Role.PARENT
        self.parent.profile.save(update_fields=["team", "role"])
        self.facility = Facility.objects.create(team=self.team, name="Main Farm")
        self.feed_room = FacilitySpace.objects.create(
            facility=self.facility, name="Feed Room",
            space_type=FacilitySpace.SpaceType.FEED_ROOM, inventory_storage_capable=True,
        )
        self.category = InventoryCategory.objects.create(team=self.team, name="Feed")
        self.item = InventoryItem.objects.create(
            team=self.team, category=self.category, name="Senior Feed",
            unit="bag", reorder_level=Decimal("5"),
        )
        self.other_item = InventoryItem.objects.create(
            team=self.other_team, name="Other Feed", unit="bag"
        )

    def test_inventory_list_is_organization_scoped(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("inventory_list"))
        self.assertContains(response, self.item.name)
        self.assertNotContains(response, self.other_item.name)

    def test_inventory_detail_rejects_cross_organization_item(self):
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.get(reverse("inventory_item_detail", args=[self.other_item.pk])).status_code,
            404,
        )

    def test_manager_can_create_item(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("inventory_item_create"), {
            "category": self.category.pk, "name": "Shavings", "unit": "bag",
            "sku": "", "reorder_level": "10", "active": "on", "notes": "",
        })
        item = InventoryItem.objects.get(team=self.team, name="Shavings")
        self.assertRedirects(response, reverse("inventory_item_detail", args=[item.pk]))

    def test_non_manager_cannot_manage_inventory(self):
        self.client.force_login(self.parent)
        self.assertEqual(self.client.get(reverse("inventory_item_create")).status_code, 403)
        self.assertEqual(self.client.get(reverse("inventory_receive", args=[self.item.pk])).status_code, 403)

    def test_receive_use_adjust_and_transfer_actions_are_visible(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("inventory_item_detail", args=[self.item.pk]))
        for label in ("Receive", "Use", "Adjust", "Transfer"):
            self.assertContains(response, label)

    def test_receive_workflow_updates_stock(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("inventory_receive", args=[self.item.pk]), {
            "space": self.feed_room.pk, "quantity": "12", "reference": "", "notes": "",
        })
        self.assertRedirects(response, reverse("inventory_item_detail", args=[self.item.pk]))
        self.assertEqual(
            InventoryStock.objects.get(item=self.item, space=self.feed_room).quantity,
            Decimal("12"),
        )

    def test_low_stock_is_visible_on_overview(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("inventory_list"))
        self.assertContains(response, "Low stock")

    def test_navigation_exposes_inventory_workspace(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("inventory_list"))
        self.assertContains(response, reverse("inventory_list"))
        self.assertContains(response, ">Inventory<", html=False)
