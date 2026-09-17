import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("portal", "0086_v340_lesson_participant_move_initiator_field")]

    operations = [
        migrations.AlterModelOptions(
            name="lessonparticipantmove",
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.RemoveConstraint(
            model_name="lessonoccurrence",
            name="unique_lesson_series_scheduled_slot",
        ),
        migrations.AlterField(
            model_name="legacyiealessonoccurrencelink",
            name="occurrence",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="legacy_iea_link",
                to="portal.lessonoccurrence",
            ),
        ),
        migrations.AlterField(
            model_name="lessonoccurrence",
            name="origin",
            field=models.CharField(
                choices=[
                    ("generated", "Generated"),
                    ("manual", "Manual"),
                    ("legacy", "Legacy"),
                ],
                default="manual",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="lessonoccurrence",
            name="scheduled_for",
            field=models.DateTimeField(editable=False, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name="lessonoccurrence",
            name="title",
            field=models.CharField(max_length=180),
        ),
        migrations.AddConstraint(
            model_name="lessonoccurrence",
            constraint=models.UniqueConstraint(
                fields=("series", "scheduled_for"),
                name="unique_lesson_series_scheduled_for",
            ),
        ),
    ]
