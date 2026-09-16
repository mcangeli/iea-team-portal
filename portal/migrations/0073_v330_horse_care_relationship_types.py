from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0072_v330_horse_identifiers"),
    ]

    operations = [
        migrations.AlterField(
            model_name="horsepersonrelationship",
            name="relationship_type",
            field=models.CharField(
                choices=[
                    ("owner", "Owner"),
                    ("boarder", "Boarder / Responsible Party"),
                    ("full_lease", "Full Lease"),
                    ("half_lease", "Half Lease"),
                    ("partial_lease", "Partial Lease"),
                    ("trainer", "Trainer"),
                    ("caretaker", "Caretaker"),
                    ("veterinarian", "Veterinarian"),
                    ("farrier", "Farrier"),
                    ("dentist", "Equine Dentist"),
                    ("emergency_contact", "Emergency Contact"),
                ],
                max_length=24,
            ),
        ),
    ]