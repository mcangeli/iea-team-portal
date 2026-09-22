from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from portal.models import Team
from portal.model_modules.facilities import Facility, FacilitySpace

# Preview 1 contract tests intentionally import the new models before
# implementation. They define the v3.8.4 basic inventory boundary first.
from portal.model_modules.inventory import (
    InventoryCategory,
    InventoryItem,
    InventoryStock,
    InventoryTransaction,
)


class InventoryFoundationContractTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Inventory Barn")
        self.other_team = Team.objects.create(name="Other Barn")
        self.facility = Facility.objects.create(team=self.team, name="Main Farm")
        self.other_facility = Facility.objects.create(team=self.other_team, name="Other Farm")
        self.feed_room = FacilitySpace.objects.create(
            facility=self.facility,
            name="Feed Room",
            space_type=FacilitySpace.SpaceType.FEED_ROOM,
            inventory_storage_capable=True,
        )
        self.trailer = FacilitySpace.objects.create(
            facility=self.facility,
            name="Show Trailer",
            space_type=FacilitySpace.SpaceType.STORAGE,
            inventory_storage_capable=True,
        )
        self.non_storage = FacilitySpace.objects.create(
            facility=self.facility,
            name="Indoor Arena",
            space_type=FacilitySpace.SpaceType.ARENA,
        )
        self.other_storage = FacilitySpace.objects.create(
            facility=self.other_facility,
            name="Other Feed Room",
            space_type=FacilitySpace.SpaceType.FEED_ROOM,
            inventory_storage_capable=True,
        )
        self.category = InventoryCategory.objects.create(team=self.team, name="Feed")
        self.item = InventoryItem.objects.create(
            team=self.team,
            category=self.category,
            name="Triple Crown Senior",
            unit="bag",
            reorder_level=Decimal("6"),
        )

    def test_category_and_item_are_organization_scoped(self):
        self.assertEqual(self.item.team, self.team)
        self.assertEqual(self.item.category, self.category)

    def test_item_category_must_belong_to_same_organization(self):
        other_category = InventoryCategory.objects.create(team=self.other_team, name="Feed")
        item = InventoryItem(
            team=self.team, category=other_category, name="Bad Item", unit="each"
        )
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_stock_requires_inventory_storage_capable_space(self):
        stock = InventoryStock(item=self.item, space=self.feed_room, quantity=Decimal("10"))
        stock.full_clean()
        with self.assertRaises(ValidationError):
            InventoryStock(
                item=self.item, space=self.non_storage, quantity=Decimal("1")
            ).full_clean()

    def test_stock_must_stay_in_same_organization(self):
        with self.assertRaises(ValidationError):
            InventoryStock(
                item=self.item, space=self.other_storage, quantity=Decimal("1")
            ).full_clean()

    def test_one_stock_balance_per_item_and_location(self):
        InventoryStock.objects.create(item=self.item, space=self.feed_room, quantity=Decimal("10"))
        duplicate = InventoryStock(item=self.item, space=self.feed_room, quantity=Decimal("2"))
        with self.assertRaises(ValidationError):
            duplicate.full_clean()

    def test_stock_quantity_cannot_be_negative(self):
        with self.assertRaises(ValidationError):
            InventoryStock(
                item=self.item, space=self.feed_room, quantity=Decimal("-1")
            ).full_clean()

    def test_receive_consume_adjust_and_transfer_are_supported(self):
        values = {value for value, _label in InventoryTransaction.TransactionType.choices}
        self.assertTrue({"receive", "consume", "adjust", "transfer_in", "transfer_out"} <= values)

    def test_transaction_requires_positive_quantity(self):
        transaction = InventoryTransaction(
            item=self.item,
            space=self.feed_room,
            transaction_type=InventoryTransaction.TransactionType.RECEIVE,
            quantity=Decimal("0"),
        )
        with self.assertRaises(ValidationError):
            transaction.full_clean()

    def test_transaction_must_stay_in_item_organization(self):
        transaction = InventoryTransaction(
            item=self.item,
            space=self.other_storage,
            transaction_type=InventoryTransaction.TransactionType.RECEIVE,
            quantity=Decimal("1"),
        )
        with self.assertRaises(ValidationError):
            transaction.full_clean()

    def test_item_can_have_stock_in_multiple_locations(self):
        InventoryStock.objects.create(item=self.item, space=self.feed_room, quantity=Decimal("14"))
        InventoryStock.objects.create(item=self.item, space=self.trailer, quantity=Decimal("3"))
        self.assertEqual(
            sum((stock.quantity for stock in self.item.stock_balances.all()), Decimal("0")),
            Decimal("17"),
        )

    def test_reorder_level_is_item_level_information(self):
        self.assertEqual(self.item.reorder_level, Decimal("6"))
        self.assertEqual(self.item.total_on_hand, Decimal("0"))
        self.assertTrue(self.item.is_low_stock)

    def test_inventory_has_no_finance_or_purchasing_dependency(self):
        item_fields = {field.name for field in InventoryItem._meta.fields}
        transaction_fields = {field.name for field in InventoryTransaction._meta.fields}
        forbidden = {
            "vendor", "payable_party", "payable_obligation", "purchase_order",
            "financial_transaction", "financial_category",
        }
        self.assertFalse(item_fields & forbidden)
        self.assertFalse(transaction_fields & forbidden)
