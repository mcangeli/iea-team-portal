from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from portal.models import Team
from portal.model_modules.facilities import Facility, FacilitySpace
from portal.model_modules.inventory import InventoryItem, InventoryStock, InventoryTransaction
from portal.services.inventory_operations import (
    adjust_inventory,
    consume_inventory,
    receive_inventory,
    transfer_inventory,
)


class InventoryOperationsTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Operations Barn")
        self.facility = Facility.objects.create(team=self.team, name="Main Farm")
        self.feed_room = FacilitySpace.objects.create(
            facility=self.facility, name="Feed Room",
            space_type=FacilitySpace.SpaceType.FEED_ROOM,
            inventory_storage_capable=True,
        )
        self.trailer = FacilitySpace.objects.create(
            facility=self.facility, name="Show Trailer",
            space_type=FacilitySpace.SpaceType.STORAGE,
            inventory_storage_capable=True,
        )
        self.item = InventoryItem.objects.create(
            team=self.team, name="Senior Feed", unit="bag", reorder_level=Decimal("5")
        )

    def quantity(self, space):
        stock = InventoryStock.objects.filter(item=self.item, space=space).first()
        return stock.quantity if stock else Decimal("0")

    def test_receive_adds_stock_and_history(self):
        tx = receive_inventory(item=self.item, space=self.feed_room, quantity=Decimal("12"))
        self.assertEqual(self.quantity(self.feed_room), Decimal("12"))
        self.assertEqual(tx.transaction_type, InventoryTransaction.TransactionType.RECEIVE)

    def test_consume_reduces_stock_and_rejects_insufficient_quantity(self):
        receive_inventory(item=self.item, space=self.feed_room, quantity=Decimal("10"))
        consume_inventory(item=self.item, space=self.feed_room, quantity=Decimal("3"))
        self.assertEqual(self.quantity(self.feed_room), Decimal("7"))
        with self.assertRaises(ValidationError):
            consume_inventory(item=self.item, space=self.feed_room, quantity=Decimal("8"))
        self.assertEqual(self.quantity(self.feed_room), Decimal("7"))

    def test_adjust_sets_physical_count_and_records_difference(self):
        receive_inventory(item=self.item, space=self.feed_room, quantity=Decimal("10"))
        tx = adjust_inventory(item=self.item, space=self.feed_room, quantity=Decimal("8"))
        self.assertEqual(self.quantity(self.feed_room), Decimal("8"))
        self.assertEqual(tx.quantity, Decimal("2"))
        self.assertEqual(tx.adjustment_direction, InventoryTransaction.AdjustmentDirection.DECREASE)

    def test_adjust_up_records_increase(self):
        receive_inventory(item=self.item, space=self.feed_room, quantity=Decimal("8"))
        tx = adjust_inventory(item=self.item, space=self.feed_room, quantity=Decimal("10"))
        self.assertEqual(tx.quantity, Decimal("2"))
        self.assertEqual(tx.adjustment_direction, InventoryTransaction.AdjustmentDirection.INCREASE)

    def test_transfer_moves_stock_and_links_history(self):
        receive_inventory(item=self.item, space=self.feed_room, quantity=Decimal("10"))
        out_tx, in_tx = transfer_inventory(
            item=self.item, source_space=self.feed_room,
            destination_space=self.trailer, quantity=Decimal("4"),
        )
        self.assertEqual(self.quantity(self.feed_room), Decimal("6"))
        self.assertEqual(self.quantity(self.trailer), Decimal("4"))
        self.assertEqual(out_tx.transfer_key, in_tx.transfer_key)
        self.assertTrue(out_tx.transfer_key)
        self.assertEqual(out_tx.transaction_type, InventoryTransaction.TransactionType.TRANSFER_OUT)
        self.assertEqual(in_tx.transaction_type, InventoryTransaction.TransactionType.TRANSFER_IN)

    def test_transfer_rejects_same_location(self):
        receive_inventory(item=self.item, space=self.feed_room, quantity=Decimal("2"))
        with self.assertRaises(ValidationError):
            transfer_inventory(
                item=self.item, source_space=self.feed_room,
                destination_space=self.feed_room, quantity=Decimal("1"),
            )

    def test_failed_transfer_preserves_source_stock_and_history(self):
        receive_inventory(item=self.item, space=self.feed_room, quantity=Decimal("2"))
        before = InventoryTransaction.objects.count()
        with self.assertRaises(ValidationError):
            transfer_inventory(
                item=self.item, source_space=self.feed_room,
                destination_space=self.trailer, quantity=Decimal("3"),
            )
        self.assertEqual(self.quantity(self.feed_room), Decimal("2"))
        self.assertEqual(self.quantity(self.trailer), Decimal("0"))
        self.assertEqual(InventoryTransaction.objects.count(), before)

    def test_zero_quantity_operations_are_rejected(self):
        for operation in (receive_inventory, consume_inventory):
            with self.assertRaises(ValidationError):
                operation(item=self.item, space=self.feed_room, quantity=Decimal("0"))
