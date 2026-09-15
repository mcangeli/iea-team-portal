import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0075_v330_care_schedule_choices"),
    ]

    operations = [
        migrations.CreateModel(
            name="HorseDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("document_type", models.CharField(choices=[("registration", "Registration papers"), ("vaccination", "Vaccination record"), ("lease", "Lease agreement"), ("ownership", "Ownership document"), ("veterinary", "Veterinary document"), ("insurance", "Insurance document"), ("care", "Care document"), ("other", "Other")], max_length=24)),
                ("title", models.CharField(max_length=160)),
                ("file", models.FileField(upload_to="horses/documents/%Y/%m/")),
                ("effective_date", models.DateField(blank=True, null=True)),
                ("expiration_date", models.DateField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("care_record", models.ForeignKey(blank=True, help_text="Optional care event this document supports.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="documents", to="portal.horsecarerecord")),
                ("horse", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="documents", to="portal.horse")),
            ],
            options={"ordering": ["document_type", "title", "-effective_date", "-id"]},
        ),
        migrations.AddIndex(
            model_name="horsedocument",
            index=models.Index(fields=["horse", "expiration_date"], name="horse_doc_expiry_idx"),
        ),
        migrations.AddIndex(
            model_name="horsedocument",
            index=models.Index(fields=["document_type", "expiration_date"], name="horse_doc_type_exp_idx"),
        ),
    ]
