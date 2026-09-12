from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("portal", "0045_v250_host_show_operations"),
    ]

    operations = [
        migrations.CreateModel(
            name="HostShowReadinessCheckpoint",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=180)),
                ("due_at", models.DateTimeField(blank=True, null=True)),
                ("status", models.CharField(choices=[("open", "Open"), ("complete", "Complete"), ("waived", "Waived")], default="open", max_length=20)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("operations", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="readiness_checkpoints", to="portal.hostshowoperations")),
                ("owner", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="host_show_readiness_checkpoints", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["status", "due_at", "sort_order", "title"]},
        ),
        migrations.CreateModel(
            name="HostShowDutyAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("area", models.CharField(choices=[("gate", "Gate / in-gate"), ("ring", "Ring operations"), ("warmup", "Warm-up / schooling"), ("checkin", "Check-in / secretary"), ("parking", "Parking / traffic"), ("hospitality", "Hospitality"), ("horses", "Horse operations"), ("runner", "Runner / communications"), ("setup", "Setup / teardown"), ("other", "Other")], default="other", max_length=20)),
                ("title", models.CharField(max_length=180)),
                ("assigned_name", models.CharField(blank=True, help_text="Use for a volunteer or staff member without a portal login.", max_length=160)),
                ("location", models.CharField(blank=True, max_length=160)),
                ("starts_at", models.DateTimeField(blank=True, null=True)),
                ("ends_at", models.DateTimeField(blank=True, null=True)),
                ("status", models.CharField(choices=[("planned", "Planned"), ("checked_in", "Checked in"), ("active", "On duty"), ("handed_off", "Handed off"), ("complete", "Complete")], default="planned", max_length=20)),
                ("instructions", models.TextField(blank=True)),
                ("handoff_notes", models.TextField(blank=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("assigned_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="host_show_duties", to=settings.AUTH_USER_MODEL)),
                ("operations", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="duty_assignments", to="portal.hostshowoperations")),
                ("relieved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="host_show_duty_handoffs", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["starts_at", "sort_order", "area", "title"]},
        ),
    ]