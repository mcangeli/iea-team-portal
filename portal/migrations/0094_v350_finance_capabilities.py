from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("portal", "0093_v350_repair_legacy_receivable_allocations")]

    operations = [
        migrations.AlterField(
            model_name="organizationcapabilityassignment",
            name="capability",
            field=models.CharField(
                choices=[
                    ("manage_horses", "Manage Horses"),
                    ("manage_iea_finance", "Manage IEA Finance"),
                    ("manage_all_finance", "Manage All Finance"),
                ],
                max_length=40,
            ),
        ),
    ]
