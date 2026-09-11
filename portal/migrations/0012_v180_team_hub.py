from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0011_v170_season_history_reporting"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="calendarevent",
            name="rsvp_requested",
            field=models.BooleanField(default=False, help_text="Ask riders/families to respond Going, Maybe, or Not going."),
        ),
        migrations.AddField(
            model_name="calendarevent",
            name="rsvp_deadline",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="EventRSVP",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("pending", "No response"), ("going", "Going"), ("maybe", "Maybe"), ("not_going", "Not going")], default="pending", max_length=20)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("responded_at", models.DateTimeField(blank=True, null=True)),
                ("event", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="rsvps", to="portal.calendarevent")),
                ("responded_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="event_rsvp_responses", to=settings.AUTH_USER_MODEL)),
                ("rider", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="event_rsvps", to="portal.rider")),
            ],
            options={"ordering": ["rider__last_name", "rider__first_name"]},
        ),
        migrations.AddConstraint(
            model_name="eventrsvp",
            constraint=models.UniqueConstraint(fields=("event", "rider"), name="unique_event_rider_rsvp"),
        ),
        migrations.CreateModel(
            name="ActionItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=180)),
                ("category", models.CharField(choices=[("rsvp", "RSVP / response"), ("volunteer", "Volunteer"), ("supply", "Bring / supply"), ("paperwork", "Paperwork"), ("task", "Task"), ("other", "Other")], default="task", max_length=20)),
                ("details", models.TextField(blank=True)),
                ("due_at", models.DateTimeField(blank=True, null=True)),
                ("family_visible", models.BooleanField(default=True)),
                ("claimable", models.BooleanField(default=False)),
                ("completed", models.BooleanField(default=False)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("assigned_to", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assigned_action_items", to=settings.AUTH_USER_MODEL)),
                ("claimed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="claimed_action_items", to=settings.AUTH_USER_MODEL)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_action_items", to=settings.AUTH_USER_MODEL)),
                ("event", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="action_items", to="portal.calendarevent")),
                ("rider", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="action_items", to="portal.rider")),
                ("season", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="action_items", to="portal.season")),
                ("show", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="action_items", to="portal.show")),
                ("team", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="action_items", to="portal.team")),
            ],
            options={"ordering": ["completed", "due_at", "-created_at"]},
        ),
    ]
