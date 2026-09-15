import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0073_v330_horse_care_relationship_types"),
    ]

    operations = [
        migrations.CreateModel(
            name="HorseCareRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("care_type", models.CharField(choices=[("vaccination", "Vaccination"), ("farrier", "Farrier"), ("dental", "Dental"), ("veterinary", "Veterinary visit"), ("coggins", "Coggins"), ("medication", "Medication / treatment"), ("wellness", "Wellness / routine care"), ("other", "Other")], max_length=24)),
                ("title", models.CharField(help_text="Short description, such as Spring vaccines, front shoes, or dental float.", max_length=160)),
                ("performed_date", models.DateField()),
                ("next_due_date", models.DateField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("horse", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="care_records", to="portal.horse")),
                ("provider", models.ForeignKey(blank=True, help_text="Optional provider from the organization's People directory.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="horse_care_records", to="portal.person")),
            ],
            options={"ordering": ["-performed_date", "-id"]},
        ),
        migrations.AddIndex(
            model_name="horsecarerecord",
            index=models.Index(fields=["horse", "next_due_date"], name="horse_care_due_idx"),
        ),
        migrations.AddIndex(
            model_name="horsecarerecord",
            index=models.Index(fields=["care_type", "next_due_date"], name="horse_care_type_due_idx"),
        ),
    ]
