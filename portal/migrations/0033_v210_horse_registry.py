from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0032_v200_squad_hero_images"),
    ]

    operations = [
        migrations.CreateModel(
            name="Horse",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("show_name", models.CharField(blank=True, help_text="Optional show name if different from barn name.", max_length=120)),
                ("breed", models.CharField(blank=True, max_length=120)),
                ("size_type", models.CharField(blank=True, help_text="Example: horse, large pony, medium pony.", max_length=80)),
                ("height_hands", models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True)),
                ("has_height_restriction", models.BooleanField(default=False)),
                ("height_restriction_notes", models.CharField(blank=True, max_length=255)),
                ("has_weight_restriction", models.BooleanField(default=False)),
                ("weight_restriction_notes", models.CharField(blank=True, max_length=255)),
                ("crop_preference", models.CharField(choices=[("yes", "Yes"), ("no", "No"), ("optional", "Optional")], default="optional", max_length=12)),
                ("spur_preference", models.CharField(choices=[("yes", "Yes"), ("no", "No"), ("optional", "Optional")], default="optional", max_length=12)),
                ("lead_change", models.CharField(choices=[("flying", "Flying"), ("simple", "Simple"), ("either", "Either"), ("none", "None / not applicable")], default="either", max_length=12)),
                ("riding_description", models.TextField(blank=True, help_text="Short description for riders and Hoofprint paperwork.")),
                ("ownership_type", models.CharField(choices=[("team", "Team-owned"), ("private", "Privately contributed"), ("leased", "Leased"), ("other", "Other")], default="private", max_length=12)),
                ("owner_name", models.CharField(blank=True, max_length=160)),
                ("home_barn", models.CharField(blank=True, max_length=160)),
                ("notes", models.TextField(blank=True)),
                ("photo", models.ImageField(blank=True, null=True, upload_to="horses/")),
                ("active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("team", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="horses", to="portal.team")),
            ],
            options={"ordering": ["name", "id"]},
        ),
        migrations.CreateModel(
            name="HorseCogginsRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("test_date", models.DateField()),
                ("expiration_date", models.DateField()),
                ("document", models.FileField(blank=True, null=True, upload_to="horses/coggins/%Y/%m/")),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("horse", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="coggins_records", to="portal.horse")),
            ],
            options={"ordering": ["-expiration_date", "-test_date", "-id"]},
        ),
        migrations.CreateModel(
            name="HorseSeasonProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("active_for_season", models.BooleanField(default=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("eligible_classes", models.ManyToManyField(blank=True, related_name="eligible_horse_profiles", to="portal.seasonclass")),
                ("horse", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="season_profiles", to="portal.horse")),
                ("season", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="horse_profiles", to="portal.season")),
            ],
            options={"ordering": ["-season__start_date", "horse__name"]},
        ),
        migrations.AddConstraint(
            model_name="horse",
            constraint=models.UniqueConstraint(fields=("team", "name"), name="unique_horse_name_per_team"),
        ),
        migrations.AddConstraint(
            model_name="horseseasonprofile",
            constraint=models.UniqueConstraint(fields=("horse", "season"), name="unique_horse_season_profile"),
        ),
    ]
