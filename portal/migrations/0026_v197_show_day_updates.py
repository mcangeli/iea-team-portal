from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0025_v1961_fundraising_policy"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="email_show_updates",
            field=models.BooleanField(default=True),
        ),
        migrations.CreateModel(
            name="ShowDayUpdate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("audience", models.CharField(
                    choices=[("all", "Everyone"), ("futures", "Futures Team"), ("upper", "Upper School Team")],
                    default="all", max_length=20,
                )),
                ("title", models.CharField(max_length=160)),
                ("body", models.TextField()),
                ("send_email", models.BooleanField(
                    default=True,
                    help_text="Also email recipients who allow show-day update email.",
                )),
                ("published", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="show_day_updates_created", to=settings.AUTH_USER_MODEL,
                )),
                ("show", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="day_updates", to="portal.show",
                )),
                ("updated_by", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="show_day_updates_updated", to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.AddField(
            model_name="notification",
            name="show_day_update",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="notifications",
                to="portal.showdayupdate",
            ),
        ),
    ]
