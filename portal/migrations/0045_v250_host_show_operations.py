from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("portal", "0044_v215_post_show_horse_history"),
    ]

    operations = [
        migrations.CreateModel(
            name="HostShowOperations",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("show_manager_name", models.CharField(blank=True, max_length=160)),
                ("show_manager_email", models.EmailField(blank=True, max_length=254)),
                ("show_manager_phone", models.CharField(blank=True, max_length=40)),
                ("venue_contact", models.CharField(blank=True, max_length=160)),
                ("venue_contact_phone", models.CharField(blank=True, max_length=40)),
                ("arrival_instructions", models.TextField(blank=True)),
                ("check_in_location", models.CharField(blank=True, max_length=180)),
                ("trailer_parking", models.TextField(blank=True)),
                ("spectator_parking", models.TextField(blank=True)),
                ("warmup_schooling", models.TextField(blank=True)),
                ("ring_operations", models.TextField(blank=True)),
                ("hospitality", models.TextField(blank=True)),
                ("volunteer_check_in", models.TextField(blank=True)),
                ("emergency_information", models.TextField(blank=True)),
                ("prize_list_url", models.URLField(blank=True)),
                ("schedule_url", models.URLField(blank=True)),
                ("family_notes", models.TextField(blank=True, help_text="Operational information appropriate for riders and families.")),
                ("internal_notes", models.TextField(blank=True, help_text="Private host-team notes for Coaches/Admins.")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_host_show_operations", to=settings.AUTH_USER_MODEL)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="updated_host_show_operations", to=settings.AUTH_USER_MODEL)),
                ("show", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="host_operations", to="portal.show")),
            ],
            options={"ordering": ["show__show_date", "show__name"]},
        ),
    ]
