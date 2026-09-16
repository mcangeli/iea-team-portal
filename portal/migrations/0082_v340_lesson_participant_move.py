from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("portal", "0081_v340_lesson_occurrence_schedule_identity")]
    operations = [
        migrations.CreateModel(
            name="LessonParticipantMove",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("move", "Move"), ("makeup", "Make-up")], default="makeup", max_length=12)),
                ("source_status", models.CharField(choices=[("expected", "Expected"), ("present", "Present"), ("absent", "Absent"), ("excused", "Excused"), ("no_show", "No-show"), ("cancelled", "Cancelled"), ("makeup", "Makeup")], default="excused", max_length=16)),
                ("carry_horse", models.BooleanField(default=False)),
                ("reason", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("destination_occurrence", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="participant_moves_in", to="portal.lessonoccurrence")),
                ("person", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="lesson_participant_moves", to="portal.person")),
                ("source_occurrence", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="participant_moves_out", to="portal.lessonoccurrence")),
            ],
            options={"ordering": ["-created_at", "id"]},
        ),
        migrations.AddConstraint(model_name="lessonparticipantmove", constraint=models.UniqueConstraint(fields=("source_occurrence", "destination_occurrence", "person"), name="unique_lesson_participant_move")),
    ]
