from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0008_v156_seasonclass_legacy_division_fix"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="email_announcements",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="email_reminders",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="announcement",
            name="audience",
            field=models.CharField(
                choices=[
                    ("all", "Entire team"),
                    ("futures", "Futures Team"),
                    ("upper", "Upper School Team"),
                    ("coaches", "Coaches / Admins"),
                    ("parents", "Parents / Guardians"),
                    ("riders", "Riders"),
                    ("selected", "Selected users"),
                ],
                default="all",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="announcement",
            name="send_email",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="announcement",
            name="selected_users",
            field=models.ManyToManyField(blank=True, related_name="selected_announcements", to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=180)),
                ("body", models.TextField(blank=True)),
                ("link", models.CharField(blank=True, max_length=300)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                ("announcement", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to="portal.announcement")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="portal_notifications", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
