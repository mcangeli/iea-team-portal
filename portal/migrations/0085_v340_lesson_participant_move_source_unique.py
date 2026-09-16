from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("portal", "0084_v340_legacy_lesson_occurrence_provenance")]

    operations = [
        migrations.RemoveConstraint(
            model_name="lessonparticipantmove",
            name="unique_lesson_participant_move",
        ),
        migrations.AddConstraint(
            model_name="lessonparticipantmove",
            constraint=models.UniqueConstraint(
                fields=("source_occurrence", "person"),
                name="unique_lesson_participant_move_source_person",
            ),
        ),
    ]
