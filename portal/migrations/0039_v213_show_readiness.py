from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0038_v212_season_class_codes"),
    ]

    operations = [
        migrations.AddField(
            model_name="season",
            name="rides_per_contributed_horse",
            field=models.PositiveSmallIntegerField(
                default=5,
                help_text="Number of rider class rides covered by each contributed horse. IEA currently requires one horse for every five rides.",
            ),
        ),
        migrations.CreateModel(
            name="ShowLeasedHorse",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("barn_name", models.CharField(max_length=120)),
                ("show_name", models.CharField(blank=True, max_length=120)),
                ("provider", models.CharField(blank=True, help_text="Barn, owner, or organization providing the leased horse.", max_length=160)),
                ("breed", models.CharField(blank=True, max_length=120)),
                ("sex", models.CharField(blank=True, choices=[("mare", "Mare"), ("gelding", "Gelding"), ("stallion", "Stallion"), ("other", "Other / not specified")], max_length=12)),
                ("size_type", models.CharField(blank=True, max_length=80)),
                ("height_hands", models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True)),
                ("available", models.BooleanField(default=True)),
                ("crop_preference", models.CharField(choices=[("yes", "Yes"), ("no", "No"), ("optional", "Optional")], default="optional", max_length=12)),
                ("spur_preference", models.CharField(choices=[("yes", "Yes"), ("no", "No"), ("optional", "Optional")], default="optional", max_length=12)),
                ("lead_change", models.CharField(choices=[("flying", "Flying"), ("simple", "Simple"), ("either", "Either"), ("none", "None / not applicable")], default="either", max_length=12)),
                ("riding_description", models.TextField(blank=True)),
                ("restriction_notes", models.CharField(blank=True, max_length=255)),
                ("coggins_status", models.CharField(blank=True, help_text="Optional show-day Coggins status or expiration note.", max_length=40)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("show", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="leased_horses", to="portal.show")),
                ("show_classes", models.ManyToManyField(blank=True, related_name="leased_horses", to="portal.showclass")),
            ],
            options={"ordering": ["barn_name", "id"]},
        ),
        migrations.AddConstraint(
            model_name="showleasedhorse",
            constraint=models.UniqueConstraint(fields=("show", "barn_name"), name="unique_leased_horse_name_per_show"),
        ),
    ]
