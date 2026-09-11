from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0010_v161_committees_show_planning"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="season", name="is_closed",
            field=models.BooleanField(default=False, help_text="Closed seasons are archived and protected from normal operational edits."),
        ),
        migrations.AddField(
            model_name="season", name="closed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="RiderDevelopmentNote",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("note", models.TextField()),
                ("family_visible", models.BooleanField(default=False, help_text="Allow the rider and linked guardians to read this note.")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("author", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="rider_development_notes", to=settings.AUTH_USER_MODEL)),
                ("rider", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="development_notes", to="portal.rider")),
                ("season", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="development_notes", to="portal.season")),
            ],
            options={"ordering":["-created_at"]},
        ),
        migrations.CreateModel(
            name="RiderAward",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=140)),
                ("description", models.TextField(blank=True)),
                ("presentation_date", models.DateField(blank=True, null=True)),
                ("published", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="rider_awards_created", to=settings.AUTH_USER_MODEL)),
                ("rider", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="awards", to="portal.rider")),
                ("season", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="awards", to="portal.season")),
            ],
            options={"ordering":["season__start_date","title"]},
        ),
        migrations.AddConstraint(
            model_name="rideraward",
            constraint=models.UniqueConstraint(fields=("season","rider","title"), name="unique_season_rider_award"),
        ),
    ]
