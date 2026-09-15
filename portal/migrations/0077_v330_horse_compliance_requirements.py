from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0076_horsedocument"),
    ]

    operations = [
        migrations.CreateModel(
            name="HorseComplianceRequirement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("requirement_type", models.CharField(choices=[("coggins", "Coggins"), ("document", "Horse document")], max_length=16)),
                ("document_type", models.CharField(blank=True, choices=[("registration", "Registration papers"), ("vaccination", "Vaccination record"), ("lease", "Lease agreement"), ("ownership", "Ownership document"), ("veterinary", "Veterinary document"), ("insurance", "Insurance document"), ("care", "Care document"), ("other", "Other")], max_length=24)),
                ("active", models.BooleanField(default=True)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("team", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="horse_compliance_requirements", to="portal.team")),
            ],
            options={"ordering": ["name", "id"]},
        ),
        migrations.AddConstraint(
            model_name="horsecompliancerequirement",
            constraint=models.UniqueConstraint(fields=("team", "name"), name="unique_horse_compliance_requirement_name"),
        ),
    ]
