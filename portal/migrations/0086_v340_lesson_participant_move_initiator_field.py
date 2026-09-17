from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("portal", "0085_v340_lesson_participant_move_source_unique")]

    operations = [
        migrations.RenameField(
            model_name="lessonparticipantmove",
            old_name="created_by",
            new_name="initiated_by_user",
        ),
        migrations.AlterField(
            model_name="lessonparticipantmove",
            name="initiated_by_user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="lesson_participant_moves_initiated",
                to="auth.user",
            ),
        ),
    ]
