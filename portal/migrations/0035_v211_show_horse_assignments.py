from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0034_v210_horse_sex"),
    ]

    operations = [
        migrations.CreateModel(
            name="HorseShowAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("available", models.BooleanField(default=True)),
                ("crop_preference", models.CharField(blank=True, choices=[("yes", "Yes"), ("no", "No"), ("optional", "Optional")], help_text="Leave blank to use the horse registry default.", max_length=12)),
                ("spur_preference", models.CharField(blank=True, choices=[("yes", "Yes"), ("no", "No"), ("optional", "Optional")], help_text="Leave blank to use the horse registry default.", max_length=12)),
                ("lead_change", models.CharField(blank=True, choices=[("flying", "Flying"), ("simple", "Simple"), ("either", "Either"), ("none", "None / not applicable")], help_text="Leave blank to use the horse registry default.", max_length=12)),
                ("notes", models.TextField(blank=True, help_text="Show-specific notes for this horse.")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("horse", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="show_assignments", to="portal.horse")),
                ("show", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="horse_assignments", to="portal.show")),
                ("show_classes", models.ManyToManyField(blank=True, related_name="horse_assignments", to="portal.showclass")),
            ],
            options={"ordering": ["horse__name", "id"]},
        ),
        migrations.AddConstraint(
            model_name="horseshowassignment",
            constraint=models.UniqueConstraint(fields=("show", "horse"), name="unique_horse_per_show"),
        ),
    ]
