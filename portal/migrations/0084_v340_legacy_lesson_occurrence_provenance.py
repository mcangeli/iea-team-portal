from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("portal", "0083_v340_lesson_participant_move_audit")]

    operations = [
        migrations.CreateModel(
            name="LegacyIEALessonOccurrenceLink",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("team_level", models.CharField(choices=[("futures", "Futures Team"), ("upper", "Upper School Team")], max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("legacy_lesson", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="v340_occurrence_links", to="portal.lesson")),
                ("occurrence", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="legacy_iea_provenance", to="portal.lessonoccurrence")),
            ],
            options={"ordering": ["legacy_lesson_id", "team_level", "id"]},
        ),
        migrations.AddConstraint(
            model_name="legacyiealessonoccurrencelink",
            constraint=models.UniqueConstraint(fields=("legacy_lesson", "team_level"), name="unique_legacy_iea_lesson_team_level_link"),
        ),
    ]
