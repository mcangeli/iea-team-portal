from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0068_v320_legacy_committee_bridge"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="StationDevice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("device_key", models.CharField(editable=False, max_length=64, unique=True)),
                ("secret_hash", models.CharField(editable=False, max_length=128)),
                ("active", models.BooleanField(default=True)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("last_seen_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("team", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="station_devices", to="portal.team")),
            ],
            options={"ordering": ["name", "id"]},
        ),
        migrations.CreateModel(
            name="StationCredential",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("pin_hash", models.CharField(editable=False, max_length=128)),
                ("active", models.BooleanField(default=True)),
                ("last_used_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("person", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="station_credential", to="portal.person")),
                ("team", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="station_credentials", to="portal.team")),
            ],
            options={"ordering": ["person__last_name", "person__first_name", "id"]},
        ),
        migrations.CreateModel(
            name="WorkShiftEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("working_student", "Working Student"), ("barn_staff", "Barn Staff"), ("barn_manager", "Barn Manager"), ("trainer", "Trainer"), ("assistant_trainer", "Assistant Trainer"), ("other", "Other")], default="working_student", max_length=24)),
                ("clock_in", models.DateTimeField()),
                ("clock_out", models.DateTimeField(blank=True, null=True)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="approved_work_shift_entries", to=settings.AUTH_USER_MODEL)),
                ("person", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="work_shift_entries", to="portal.person")),
                ("station", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="work_shift_entries", to="portal.stationdevice")),
                ("team", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="work_shift_entries", to="portal.team")),
            ],
            options={"ordering": ["-clock_in", "-id"]},
        ),
        migrations.AddConstraint(
            model_name="stationdevice",
            constraint=models.UniqueConstraint(fields=("team", "name"), name="unique_station_device_name_per_team"),
        ),
        migrations.AddConstraint(
            model_name="workshiftentry",
            constraint=models.UniqueConstraint(condition=models.Q(("clock_out__isnull", True)), fields=("person",), name="unique_open_work_shift_per_person"),
        ),
    ]
