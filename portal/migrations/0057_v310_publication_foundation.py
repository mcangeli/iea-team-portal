from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0056_v300_reconcile_catalog_non_team_entries"),
    ]

    operations = [
        migrations.CreateModel(
            name="PublicSiteProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=120, unique=True)),
                ("enabled", models.BooleanField(default=False, help_text="Nothing is publicly accessible for this organization until this is enabled.")),
                ("display_name", models.CharField(blank=True, max_length=160)),
                ("tagline", models.CharField(blank=True, max_length=240)),
                ("introduction", models.TextField(blank=True)),
                ("publish_logo", models.BooleanField(default=False)),
                ("publish_website", models.BooleanField(default=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("team", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="public_site", to="portal.team")),
            ],
            options={"ordering": ["team__name"]},
        ),
        migrations.CreateModel(
            name="PublicShowPublication",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=180, unique=True)),
                ("is_published", models.BooleanField(default=False, help_text="The show remains private until this is enabled and the organization public site is enabled.")),
                ("public_summary", models.TextField(blank=True)),
                ("publish_time", models.BooleanField(default=False)),
                ("publish_venue", models.BooleanField(default=False)),
                ("publish_address", models.BooleanField(default=False)),
                ("publish_host_team", models.BooleanField(default=False)),
                ("publish_iea_area", models.BooleanField(default=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("show", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="public_publication", to="portal.show")),
            ],
            options={"ordering": ["show__show_date", "show__name"]},
        ),
    ]
