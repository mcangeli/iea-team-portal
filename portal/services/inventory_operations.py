"""Atomic stock operations for ArenaLine basic inventory."""

from decimal import Decimal
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from portal.model_modules.inventory import InventoryStock, InventoryTransaction


def _quantity(value):
    value = Decimal(value)
    if value <= 0:
        raise ValidationError({"quantity": "Quantity must be greater than zero."})
    return value


def _validate_location(item, space):
    if not space.inventory_storage_capable:
        raise ValidationError({"space": "Selected facility space cannot store inventory."})
    if space.facility.team_id != item.team_id:
        raise ValidationError({"space": "Inventory item and storage space must belong to the same organization."})


def _locked_stock(item, space):
    stock, _created = InventoryStock.objects.select_for_update().get_or_create(
        item=item, space=space, defaults={"quantity": Decimal("0")}
    )
    return stock


def _history(*, item, space, transaction_type, quantity, adjustment_direction="",
             transfer_key="", reference="", notes="", occurred_at=None):
    entry = InventoryTransaction(
        item=item,
        space=space,
        transaction_type=transaction_type,
        quantity=quantity,
        adjustment_direction=adjustment_direction,
        transfer_key=transfer_key,
        reference=reference.strip(),
        notes=notes.strip(),
        occurred_at=occurred_at or timezone.now(),
    )
    entry.full_clean()
    entry.save()
    return entry


@transaction.atomic
def receive_inventory(*, item, space, quantity, reference="", notes="", occurred_at=None):
    quantity = _quantity(quantity)
    _validate_location(item, space)
    stock = _locked_stock(item, space)
    stock.quantity += quantity
    stock.full_clean()
    stock.save(update_fields=["quantity", "updated_at"])
    return _history(
        item=item, space=space, transaction_type=InventoryTransaction.TransactionType.RECEIVE,
        quantity=quantity, reference=reference, notes=notes, occurred_at=occurred_at,
    )


@transaction.atomic
def consume_inventory(*, item, space, quantity, reference="", notes="", occurred_at=None):
    quantity = _quantity(quantity)
    _validate_location(item, space)
    stock = _locked_stock(item, space)
    if stock.quantity < quantity:
        raise ValidationError({"quantity": "Cannot consume more inventory than is on hand."})
    stock.quantity -= quantity
    stock.full_clean()
    stock.save(update_fields=["quantity", "updated_at"])
    return _history(
        item=item, space=space, transaction_type=InventoryTransaction.TransactionType.CONSUME,
        quantity=quantity, reference=reference, notes=notes, occurred_at=occurred_at,
    )


@transaction.atomic
def adjust_inventory(*, item, space, quantity, reference="", notes="", occurred_at=None):
    """Set stock to a verified physical count and record only the difference."""
    target = Decimal(quantity)
    if target < 0:
        raise ValidationError({"quantity": "Physical count cannot be negative."})
    _validate_location(item, space)
    stock = _locked_stock(item, space)
    difference = target - stock.quantity
    if difference == 0:
        raise ValidationError({"quantity": "Physical count already matches inventory."})
    direction = (
        InventoryTransaction.AdjustmentDirection.INCREASE
        if difference > 0
        else InventoryTransaction.AdjustmentDirection.DECREASE
    )
    stock.quantity = target
    stock.full_clean()
    stock.save(update_fields=["quantity", "updated_at"])
    return _history(
        item=item, space=space, transaction_type=InventoryTransaction.TransactionType.ADJUST,
        quantity=abs(difference), adjustment_direction=direction,
        reference=reference, notes=notes, occurred_at=occurred_at,
    )


@transaction.atomic
def transfer_inventory(*, item, source_space, destination_space, quantity,
                       reference="", notes="", occurred_at=None):
    quantity = _quantity(quantity)
    _validate_location(item, source_space)
    _validate_location(item, destination_space)
    if source_space.pk == destination_space.pk:
        raise ValidationError({"space": "Source and destination must be different storage locations."})

    source = _locked_stock(item, source_space)
    if source.quantity < quantity:
        raise ValidationError({"quantity": "Cannot transfer more inventory than is on hand."})
    destination = _locked_stock(item, destination_space)

    source.quantity -= quantity
    destination.quantity += quantity
    source.full_clean()
    destination.full_clean()
    source.save(update_fields=["quantity", "updated_at"])
    destination.save(update_fields=["quantity", "updated_at"])

    transfer_key = uuid4().hex
    out_entry = _history(
        item=item, space=source_space,
        transaction_type=InventoryTransaction.TransactionType.TRANSFER_OUT,
        quantity=quantity, transfer_key=transfer_key, reference=reference,
        notes=notes, occurred_at=occurred_at,
    )
    in_entry = _history(
        item=item, space=destination_space,
        transaction_type=InventoryTransaction.TransactionType.TRANSFER_IN,
        quantity=quantity, transfer_key=transfer_key, reference=reference,
        notes=notes, occurred_at=occurred_at,
    )
    return out_entry, in_entry
