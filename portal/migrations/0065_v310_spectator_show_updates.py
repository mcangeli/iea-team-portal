from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0064_v310_show_class_ring_assignment"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SpectatorShowUpdate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("announcement", "Announcement"), ("delay", "Delay"), ("break", "Break"), ("schedule", "Schedule update")], default="announcement", max_length=20)),
                ("ring", models.CharField(blank=True, max_length=80)),
                ("title", models.CharField(max_length=120)),
                ("message", models.CharField(blank=True, max_length=280)),
                ("active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="spectator_show_updates_created", to=settings.AUTH_USER_MODEL)),
                ("show", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="spectator_updates", to="portal.show")),
            ],
            options={"ordering": ["-updated_at", "-id"]},
        ),
    ]
