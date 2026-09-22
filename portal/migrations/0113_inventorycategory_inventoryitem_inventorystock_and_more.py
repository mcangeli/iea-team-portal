# Generated for ArenaLine v3.8.4 basic inventory foundation.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0112_resourcereservation_cancelled_at"),
    ]

    operations = [
        migrations.CreateModel(
            name="InventoryCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("active", models.BooleanField(default=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("team", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="inventory_categories", to="portal.team")),
            ],
            options={"ordering": ["name", "id"]},
        ),
        migrations.CreateModel(
            name="InventoryItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=180)),
                ("unit", models.CharField(default="each", help_text="Unit used to count this item, such as bag, bale, bottle, or each.", max_length=40)),
                ("sku", models.CharField(blank=True, max_length=80)),
                ("reorder_level", models.DecimalField(decimal_places=3, default=0, max_digits=12)),
                ("active", models.BooleanField(default=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("category", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="items", to="portal.inventorycategory")),
                ("team", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="inventory_items", to="portal.team")),
            ],
            options={"ordering": ["name", "id"]},
        ),
        migrations.CreateModel(
            name="InventoryStock",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.DecimalField(decimal_places=3, default=0, max_digits=12)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("item", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="stock_balances", to="portal.inventoryitem")),
                ("space", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="inventory_stock", to="portal.facilityspace")),
            ],
            options={"ordering": ["item__name", "space__name", "id"]},
        ),
        migrations.CreateModel(
            name="InventoryTransaction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("transaction_type", models.CharField(choices=[("receive", "Receive"), ("consume", "Consume"), ("adjust", "Adjust"), ("transfer_in", "Transfer in"), ("transfer_out", "Transfer out")], max_length=16)),
                ("quantity", models.DecimalField(decimal_places=3, max_digits=12)),
                ("transfer_key", models.CharField(blank=True, help_text="Shared identifier linking the two sides of a transfer.", max_length=64)),
                ("reference", models.CharField(blank=True, max_length=120)),
                ("notes", models.TextField(blank=True)),
                ("occurred_at", models.DateTimeField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("item", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="transactions", to="portal.inventoryitem")),
                ("space", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="inventory_transactions", to="portal.facilityspace")),
            ],
            options={"ordering": ["-occurred_at", "-id"]},
        ),
        migrations.AddConstraint(
            model_name="inventorycategory",
            constraint=models.UniqueConstraint(fields=("team", "name"), name="unique_inventory_category_team_name"),
        ),
        migrations.AddConstraint(
            model_name="inventoryitem",
            constraint=models.UniqueConstraint(fields=("team", "name"), name="unique_inventory_item_team_name"),
        ),
        migrations.AddConstraint(
            model_name="inventoryitem",
            constraint=models.CheckConstraint(condition=models.Q(("reorder_level__gte", 0)), name="inventory_item_reorder_level_gte_zero"),
        ),
        migrations.AddConstraint(
            model_name="inventorystock",
            constraint=models.UniqueConstraint(fields=("item", "space"), name="unique_inventory_stock_item_space"),
        ),
        migrations.AddConstraint(
            model_name="inventorystock",
            constraint=models.CheckConstraint(condition=models.Q(("quantity__gte", 0)), name="inventory_stock_quantity_gte_zero"),
        ),
        migrations.AddConstraint(
            model_name="inventorytransaction",
            constraint=models.CheckConstraint(condition=models.Q(("quantity__gt", 0)), name="inventory_transaction_quantity_gt_zero"),
        ),
    ]
