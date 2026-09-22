"""ArenaLine basic inventory and supplies foundation."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum


ZERO_QUANTITY = Decimal("0")


class InventoryCategory(models.Model):
    """Organization-owned operational grouping for inventory items."""

    team = models.ForeignKey(
        "portal.Team", on_delete=models.CASCADE, related_name="inventory_categories"
    )
    name = models.CharField(max_length=120)
    active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["team", "name"], name="unique_inventory_category_team_name"
            ),
        ]

    def __str__(self):
        return self.name


class InventoryItem(models.Model):
    """Canonical inventory item; physical quantities live in InventoryStock."""

    team = models.ForeignKey(
        "portal.Team", on_delete=models.CASCADE, related_name="inventory_items"
    )
    category = models.ForeignKey(
        InventoryCategory,
        on_delete=models.PROTECT,
        related_name="items",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=180)
    unit = models.CharField(
        max_length=40,
        default="each",
        help_text="Unit used to count this item, such as bag, bale, bottle, or each.",
    )
    sku = models.CharField(max_length=80, blank=True)
    reorder_level = models.DecimalField(
        max_digits=12, decimal_places=3, default=0
    )
    active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["team", "name"], name="unique_inventory_item_team_name"
            ),
            models.CheckConstraint(
                condition=models.Q(reorder_level__gte=0),
                name="inventory_item_reorder_level_gte_zero",
            ),
        ]

    def clean(self):
        super().clean()
        if self.category_id and self.category.team_id != self.team_id:
            raise ValidationError(
                {"category": "Inventory category must belong to the same organization."}
            )

    @property
    def total_on_hand(self):
        return (
            self.stock_balances.aggregate(total=Sum("quantity"))["total"]
            or ZERO_QUANTITY
        )

    @property
    def is_low_stock(self):
        return self.total_on_hand <= self.reorder_level

    def __str__(self):
        return self.name


class InventoryStock(models.Model):
    """Materialized on-hand quantity for one item at one storage location."""

    item = models.ForeignKey(
        InventoryItem, on_delete=models.CASCADE, related_name="stock_balances"
    )
    space = models.ForeignKey(
        "portal.FacilitySpace",
        on_delete=models.PROTECT,
        related_name="inventory_stock",
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["item__name", "space__name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["item", "space"], name="unique_inventory_stock_item_space"
            ),
            models.CheckConstraint(
                condition=models.Q(quantity__gte=0),
                name="inventory_stock_quantity_gte_zero",
            ),
        ]

    def clean(self):
        super().clean()
        if self.space_id:
            if not self.space.inventory_storage_capable:
                raise ValidationError(
                    {"space": "Selected facility space cannot store inventory."}
                )
            if self.item_id and self.space.facility.team_id != self.item.team_id:
                raise ValidationError(
                    {"space": "Inventory item and storage space must belong to the same organization."}
                )
        if self.quantity is not None and self.quantity < ZERO_QUANTITY:
            raise ValidationError({"quantity": "Inventory quantity cannot be negative."})

    def __str__(self):
        return f"{self.item} — {self.space}: {self.quantity}"


class InventoryTransaction(models.Model):
    """Durable history of a physical inventory movement."""

    class TransactionType(models.TextChoices):
        RECEIVE = "receive", "Receive"
        CONSUME = "consume", "Consume"
        ADJUST = "adjust", "Adjust"
        TRANSFER_IN = "transfer_in", "Transfer in"
        TRANSFER_OUT = "transfer_out", "Transfer out"

    item = models.ForeignKey(
        InventoryItem, on_delete=models.PROTECT, related_name="transactions"
    )
    space = models.ForeignKey(
        "portal.FacilitySpace",
        on_delete=models.PROTECT,
        related_name="inventory_transactions",
    )
    transaction_type = models.CharField(
        max_length=16, choices=TransactionType.choices
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    transfer_key = models.CharField(
        max_length=64,
        blank=True,
        help_text="Shared identifier linking the two sides of a transfer.",
    )
    reference = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    occurred_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-occurred_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name="inventory_transaction_quantity_gt_zero",
            ),
        ]

    def clean(self):
        super().clean()
        if self.quantity is not None and self.quantity <= ZERO_QUANTITY:
            raise ValidationError({"quantity": "Inventory transaction quantity must be greater than zero."})
        if self.space_id:
            if not self.space.inventory_storage_capable:
                raise ValidationError(
                    {"space": "Selected facility space cannot store inventory."}
                )
            if self.item_id and self.space.facility.team_id != self.item.team_id:
                raise ValidationError(
                    {"space": "Inventory item and storage space must belong to the same organization."}
                )

    def __str__(self):
        return f"{self.get_transaction_type_display()} — {self.item}: {self.quantity}"
