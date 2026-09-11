from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("portal", "0043_alter_showbudgetline_options_alter_showentry_options_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ShowHorseHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("draft", "Draft"), ("final", "Final")], default="draft", max_length=12)),
                ("notes", models.TextField(blank=True, help_text="Post-show notes about the final horse contribution and usage record.")),
                ("finalized_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("finalized_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="finalized_show_horse_histories", to=settings.AUTH_USER_MODEL)),
                ("generated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="generated_show_horse_histories", to=settings.AUTH_USER_MODEL)),
                ("show", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="horse_history", to="portal.show")),
            ],
            options={"ordering": ["-show__show_date", "-id"]},
        ),
        migrations.CreateModel(
            name="ShowHorseHistoryRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_type", models.CharField(choices=[("registry", "Horse Registry"), ("leased", "Leased / show-specific"), ("other", "Other")], max_length=12)),
                ("barn_name", models.CharField(max_length=120)),
                ("show_name", models.CharField(blank=True, max_length=120)),
                ("provider", models.CharField(blank=True, max_length=160)),
                ("ownership_type", models.CharField(blank=True, max_length=20)),
                ("actually_used", models.BooleanField(default=True)),
                ("counted_as_contribution", models.BooleanField(default=True)),
                ("class_snapshot", models.JSONField(blank=True, default=list)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("history", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="records", to="portal.showhorsehistory")),
                ("horse", models.ForeignKey(blank=True, help_text="Registry horse actually used. A leased placeholder can be reconciled to a registry horse after the show.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="show_history_records", to="portal.horse")),
                ("source_assignment", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="history_records", to="portal.horseshowassignment")),
                ("source_leased_horse", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="history_records", to="portal.showleasedhorse")),
            ],
            options={"ordering": ["barn_name", "id"]},
        ),
    ]
