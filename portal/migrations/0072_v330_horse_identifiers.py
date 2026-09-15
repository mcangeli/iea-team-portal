from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0071_v323_null_safe_uniqueness"),
    ]

    operations = [
        migrations.CreateModel(
            name="HorseIdentifier",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("authority", models.CharField(help_text="Registry or organization, such as IEA or USEF.", max_length=100)),
                ("identifier_type", models.CharField(blank=True, help_text="Optional identifier type or program name.", max_length=80)),
                ("value", models.CharField(max_length=120)),
                ("is_primary", models.BooleanField(default=False)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("horse", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="identifiers", to="portal.horse")),
            ],
            options={"ordering": ["authority", "identifier_type", "value", "id"]},
        ),
        migrations.AddConstraint(
            model_name="horseidentifier",
            constraint=models.UniqueConstraint(
                fields=("horse", "authority", "identifier_type", "value"),
                name="unique_horse_external_identifier",
            ),
        ),
    ]
