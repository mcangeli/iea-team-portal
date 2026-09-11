from django.db import migrations, models
import django.db.models.deletion


def seed_branding(apps, schema_editor):
    Team = apps.get_model("portal", "Team")
    TeamBranding = apps.get_model("portal", "TeamBranding")
    for team in Team.objects.all():
        TeamBranding.objects.get_or_create(team=team)


class Migration(migrations.Migration):
    dependencies = [("portal", "0030_v200_rider_lifecycle")]

    operations = [
        migrations.CreateModel(
            name="TeamBranding",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("hero_image", models.ImageField(blank=True, help_text="Wide team/show photograph used on the dashboard and sign-in presentation.", null=True, upload_to="team_branding/")),
                ("hero_image_position", models.CharField(choices=[("20%", "Favor top"), ("50%", "Center"), ("80%", "Favor bottom")], default="50%", help_text="Adjust which part of the photograph remains visible when it is cropped.", max_length=8)),
                ("team", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="branding", to="portal.team")),
            ],
        ),
        migrations.RunPython(seed_branding, migrations.RunPython.noop),
    ]
