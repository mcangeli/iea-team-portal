from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0039_v213_show_readiness"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ShowCourse",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=160)),
                ("course_type", models.CharField(choices=[("over_fences", "Over fences"), ("flat", "Flat / rail"), ("warmup", "Warm-up"), ("other", "Other")], default="over_fences", max_length=20)),
                ("ring", models.CharField(blank=True, max_length=100)),
                ("course_walk_at", models.DateTimeField(blank=True, null=True)),
                ("course_designer", models.CharField(blank=True, max_length=120)),
                ("fence_count", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("combinations", models.CharField(blank=True, max_length=160)),
                ("related_distances", models.CharField(blank=True, max_length=255)),
                ("handy_options", models.CharField(blank=True, max_length=255)),
                ("posted_notes", models.TextField(blank=True, help_text="General course details suitable for the show operations workspace.")),
                ("coach_notes", models.TextField(blank=True, help_text="Private Coach/Admin notes. Not shown to riders or parents.")),
                ("course_file", models.FileField(blank=True, upload_to="course_files/")),
                ("external_link", models.URLField(blank=True)),
                ("active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_show_courses", to=settings.AUTH_USER_MODEL)),
                ("show", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="courses", to="portal.show")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="updated_show_courses", to=settings.AUTH_USER_MODEL)),
                ("show_classes", models.ManyToManyField(blank=True, related_name="courses", to="portal.showclass")),
            ],
            options={"ordering": ["ring", "course_walk_at", "title", "id"]},
        ),
    ]
