from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0033_v210_horse_registry"),
    ]

    operations = [
        migrations.AddField(
            model_name="horse",
            name="sex",
            field=models.CharField(
                blank=True,
                choices=[
                    ("mare", "Mare"),
                    ("gelding", "Gelding"),
                    ("stallion", "Stallion"),
                    ("other", "Other / not specified"),
                ],
                max_length=12,
            ),
        ),
    ]
