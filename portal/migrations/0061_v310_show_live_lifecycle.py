from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0060_v310_public_live_status"),
    ]

    operations = [
        migrations.AlterField(
            model_name="show",
            name="status",
            field=models.CharField(
                choices=[
                    ("planning", "Planning"),
                    ("registration", "Registration open"),
                    ("entered", "Entries submitted"),
                    ("in_progress", "In progress"),
                    ("paused", "Paused"),
                    ("complete", "Complete"),
                    ("cancelled", "Cancelled"),
                ],
                default="planning",
                max_length=20,
            ),
        ),
    ]
