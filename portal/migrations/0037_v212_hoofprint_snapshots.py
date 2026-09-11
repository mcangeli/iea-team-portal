from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0036_v211_horse_show_awards"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="HoofprintSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("version", models.PositiveIntegerField()),
                ("payload", models.JSONField(default=dict)),
                ("finalized_at", models.DateTimeField(auto_now_add=True)),
                (
                    "finalized_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="finalized_hoofprints",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "show",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="hoofprint_snapshots",
                        to="portal.show",
                    ),
                ),
            ],
            options={
                "ordering": ["-version", "-finalized_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="hoofprintsnapshot",
            constraint=models.UniqueConstraint(
                fields=("show", "version"),
                name="unique_hoofprint_version_per_show",
            ),
        ),
    ]
