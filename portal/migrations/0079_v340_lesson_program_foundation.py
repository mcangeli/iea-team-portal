import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("portal", "0078_v330_organization_capabilities")]

    operations = [
        migrations.CreateModel(
            name="LessonProgram",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=160)),
                ("description", models.TextField(blank=True)),
                ("default_capacity", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("enrollment_opens", models.DateField(blank=True, null=True)),
                ("enrollment_closes", models.DateField(blank=True, null=True)),
                ("active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("group", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="lesson_programs", to="portal.organizationgroup")),
                ("team", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lesson_programs", to="portal.team")),
            ],
            options={"ordering": ["name", "id"]},
        ),
        migrations.AddConstraint(
            model_name="lessonprogram",
            constraint=models.UniqueConstraint(fields=("team", "name"), name="unique_lesson_program_team_name"),
        ),
        migrations.CreateModel(
            name="LessonSeries",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=160)),
                ("weekday", models.PositiveSmallIntegerField(blank=True, help_text="Monday=0 through Sunday=6.", null=True)),
                ("starts_at_time", models.TimeField(blank=True, null=True)),
                ("duration_minutes", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("default_location", models.CharField(blank=True, max_length=180)),
                ("capacity", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("active", models.BooleanField(default=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("instructor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="lesson_series_instructed", to="portal.person")),
                ("program", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="series", to="portal.lessonprogram")),
            ],
            options={"ordering": ["program__name", "name", "id"]},
        ),
        migrations.AddConstraint(
            model_name="lessonseries",
            constraint=models.UniqueConstraint(fields=("program", "name"), name="unique_lesson_series_program_name"),
        ),
        migrations.CreateModel(
            name="LessonEnrollment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("active", "Active"), ("waitlisted", "Waitlisted"), ("withdrawn", "Withdrawn"), ("completed", "Completed")], default="active", max_length=16)),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("person", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="lesson_enrollments", to="portal.person")),
                ("series", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="enrollments", to="portal.lessonseries")),
            ],
            options={"ordering": ["person__last_name", "person__first_name", "id"]},
        ),
        migrations.AddConstraint(
            model_name="lessonenrollment",
            constraint=models.UniqueConstraint(fields=("series", "person"), name="unique_lesson_series_person_enrollment"),
        ),
        migrations.CreateModel(
            name="LessonOccurrence",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=160)),
                ("starts_at", models.DateTimeField()),
                ("ends_at", models.DateTimeField(blank=True, null=True)),
                ("location", models.CharField(blank=True, max_length=180)),
                ("capacity", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("status", models.CharField(choices=[("scheduled", "Scheduled"), ("completed", "Completed"), ("cancelled", "Cancelled"), ("rescheduled", "Rescheduled")], default="scheduled", max_length=16)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("instructor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="lesson_occurrences_instructed", to="portal.person")),
                ("series", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="occurrences", to="portal.lessonseries")),
            ],
            options={"ordering": ["starts_at", "id"]},
        ),
        migrations.CreateModel(
            name="LessonAttendanceRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("expected", "Expected"), ("present", "Present"), ("absent", "Absent"), ("excused", "Excused"), ("no_show", "No-show"), ("cancelled", "Cancelled"), ("makeup", "Makeup")], default="expected", max_length=16)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("recorded_at", models.DateTimeField(auto_now=True)),
                ("occurrence", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attendance_records", to="portal.lessonoccurrence")),
                ("person", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="lesson_attendance_records", to="portal.person")),
            ],
            options={"ordering": ["person__last_name", "person__first_name", "id"]},
        ),
        migrations.AddConstraint(
            model_name="lessonattendancerecord",
            constraint=models.UniqueConstraint(fields=("occurrence", "person"), name="unique_lesson_occurrence_person_attendance"),
        ),
        migrations.CreateModel(
            name="LessonAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("participant", "Participant"), ("instructor", "Instructor")], default="participant", max_length=16)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("horse", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="lesson_assignments", to="portal.horse")),
                ("occurrence", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="assignments", to="portal.lessonoccurrence")),
                ("person", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="lesson_assignments", to="portal.person")),
            ],
            options={"ordering": ["role", "person__last_name", "person__first_name", "id"]},
        ),
        migrations.AddConstraint(
            model_name="lessonassignment",
            constraint=models.UniqueConstraint(fields=("occurrence", "person", "role"), name="unique_lesson_occurrence_person_role"),
        ),
    ]
