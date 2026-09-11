from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0027_v197_prize_list_schedule"),
    ]

    operations = [
        migrations.CreateModel(
            name="ShowDayRiderStatus",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(
                    choices=[
                        ("expected", "Expected"),
                        ("arrived", "Arrived"),
                        ("running_late", "Running Late"),
                        ("scratched", "Scratched"),
                        ("finished", "Finished / Left"),
                    ],
                    default="expected",
                    max_length=20,
                )),
                ("note", models.CharField(blank=True, max_length=180)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("rider", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="show_day_statuses",
                    to="portal.rider",
                )),
                ("show", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="rider_statuses",
                    to="portal.show",
                )),
                ("updated_by", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="show_day_status_updates",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"ordering": ["rider__last_name", "rider__first_name"]},
        ),
        migrations.AddConstraint(
            model_name="showdayriderstatus",
            constraint=models.UniqueConstraint(
                fields=("show", "rider"),
                name="unique_show_day_rider_status",
            ),
        ),
    ]
