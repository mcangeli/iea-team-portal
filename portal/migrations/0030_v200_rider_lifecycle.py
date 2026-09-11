from django.db import migrations, models
import django.db.models.deletion


def create_lifecycle_records(apps, schema_editor):
    Rider = apps.get_model("portal", "Rider")
    RiderLifecycle = apps.get_model("portal", "RiderLifecycle")
    RiderLifecycle.objects.bulk_create([
        RiderLifecycle(
            rider_id=rider.pk,
            status="active" if rider.active else "inactive",
        )
        for rider in Rider.objects.all().only("pk", "active")
    ])


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0029_v197_show_day_planning"),
    ]

    operations = [
        migrations.CreateModel(
            name="RiderLifecycle",
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
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("graduated", "Graduated"),
                            ("left_team", "Left Team"),
                            ("inactive", "Inactive"),
                        ],
                        db_index=True,
                        default="active",
                        max_length=20,
                    ),
                ),
                (
                    "graduation_year",
                    models.PositiveSmallIntegerField(blank=True, null=True),
                ),
                (
                    "ended_on",
                    models.DateField(
                        blank=True,
                        help_text=(
                            "Optional date the rider graduated, left the team, "
                            "or otherwise became inactive."
                        ),
                        null=True,
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "rider",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lifecycle",
                        to="portal.rider",
                    ),
                ),
            ],
            options={
                "ordering": ["rider__last_name", "rider__first_name"],
            },
        ),
        migrations.RunPython(
            create_lifecycle_records,
            migrations.RunPython.noop,
        ),
    ]
