from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0050_v300_seasonclass_catalog_link"),
    ]

    operations = [
        migrations.CreateModel(
            name="IEASeasonCatalogConfiguration",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("rulebook_season", models.CharField(max_length=20)),
                ("disciplines", models.JSONField(blank=True, default=list)),
                ("configured_at", models.DateTimeField(auto_now=True)),
                (
                    "season",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="iea_catalog_configuration",
                        to="portal.season",
                    ),
                ),
            ],
            options={"ordering": ["season_id"]},
        ),
    ]
