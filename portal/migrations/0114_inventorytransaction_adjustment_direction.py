from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0113_inventorycategory_inventoryitem_inventorystock_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="inventorytransaction",
            name="adjustment_direction",
            field=models.CharField(
                blank=True,
                choices=[("increase", "Increase"), ("decrease", "Decrease")],
                max_length=8,
            ),
        ),
    ]
