from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0074_v330_horse_care_records"),
    ]

    operations = [
        migrations.AlterField(
            model_name="horse",
            name="ownership_type",
            field=models.CharField(
                choices=[
                    ("team", "Barn-owned"),
                    ("private", "Privately contributed"),
                    ("leased", "Leased"),
                    ("other", "Other"),
                ],
                default="private",
                max_length=12,
            ),
        ),
        migrations.AlterField(
            model_name="horsecarerecord",
            name="care_type",
            field=models.CharField(
                choices=[
                    ("vaccination", "Vaccination"),
                    ("farrier", "Farrier"),
                    ("dental", "Dental"),
                    ("veterinary", "Veterinary visit"),
                    ("medication", "Medication / treatment"),
                    ("wellness", "Wellness / routine care"),
                    ("other", "Other"),
                ],
                max_length=24,
            ),
        ),
    ]
