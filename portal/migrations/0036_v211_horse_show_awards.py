from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0035_v211_show_horse_assignments"),
    ]

    operations = [
        migrations.CreateModel(
            name="HorseShowAward",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("session", models.CharField(choices=[("full_day", "Full Day"), ("morning", "Morning"), ("afternoon", "Afternoon")], max_length=12)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assignment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="awards", to="portal.horseshowassignment")),
                ("show", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="horse_awards", to="portal.show")),
            ],
            options={"ordering": ["show__show_date", "session"]},
        ),
        migrations.AddConstraint(
            model_name="horseshowaward",
            constraint=models.UniqueConstraint(fields=("show", "session"), name="unique_horse_award_session_per_show"),
        ),
    ]
