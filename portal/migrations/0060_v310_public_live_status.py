from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0059_v310_public_show_results"),
    ]

    operations = [
        migrations.AddField(
            model_name="publicshowpublication",
            name="current_class",
            field=models.ForeignKey(
                blank=True,
                help_text="Optional class currently running for the public spectator view.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="portal.showclass",
            ),
        ),
        migrations.AddField(
            model_name="publicshowpublication",
            name="public_status",
            field=models.CharField(
                choices=[
                    ("upcoming", "Upcoming"),
                    ("in_progress", "In progress"),
                    ("paused", "Paused"),
                    ("complete", "Complete"),
                ],
                default="upcoming",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="publicshowpublication",
            name="public_status_note",
            field=models.CharField(
                blank=True,
                help_text="Optional public update such as 'Running about 15 minutes behind.'",
                max_length=180,
            ),
        ),
        migrations.AddField(
            model_name="publicshowpublication",
            name="publish_live_status",
            field=models.BooleanField(
                default=False,
                help_text="Publishes the spectator-facing show status and current class. Internal show-day operations remain private.",
            ),
        ),
    ]
