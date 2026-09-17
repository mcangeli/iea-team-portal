from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("portal", "0079_v340_lesson_program_foundation")]

    operations = [
        migrations.CreateModel(
            name="IEALessonSeriesContext",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("team_level", models.CharField(choices=[("futures", "Futures Team"), ("upper", "Upper School Team")], max_length=20)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("season", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="iea_lesson_series", to="portal.season")),
                ("series", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="iea_context", to="portal.lessonseries")),
            ],
            options={"ordering": ["-season__start_date", "team_level", "series__name", "id"]},
        ),
        migrations.AddConstraint(
            model_name="iealessonseriescontext",
            constraint=models.UniqueConstraint(fields=("season", "team_level", "series"), name="unique_iea_lesson_series_context"),
        ),
    ]
