import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("portal", "0088_v340_restore_lesson_participant_move_carry_horse")]

    operations = [
        migrations.RemoveConstraint(
            model_name="legacyiealessonoccurrencelink",
            name="unique_legacy_iea_lesson_team_level_link",
        ),
        migrations.RemoveConstraint(
            model_name="lessonassignment",
            name="unique_lesson_occurrence_person_role",
        ),
        migrations.AlterField(
            model_name="lessonattendancerecord",
            name="person",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="lesson_attendance",
                to="portal.person",
            ),
        ),
        migrations.AlterField(
            model_name="lessonattendancerecord",
            name="status",
            field=models.CharField(
                choices=[
                    ("expected", "Expected"),
                    ("present", "Present"),
                    ("absent", "Absent"),
                    ("excused", "Excused"),
                    ("no_show", "No show"),
                    ("makeup", "Make-up"),
                ],
                default="expected",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="lessonparticipantmove",
            name="initiated_by",
            field=models.CharField(
                choices=[("staff", "Staff"), ("rider", "Rider")],
                default="staff",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="lessonparticipantmove",
            name="kind",
            field=models.CharField(
                choices=[("move", "Move"), ("makeup", "Make-up")],
                default="move",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="lessonparticipantmove",
            name="source_status",
            field=models.CharField(
                choices=[
                    ("expected", "Expected"),
                    ("present", "Present"),
                    ("absent", "Absent"),
                    ("excused", "Excused"),
                    ("no_show", "No show"),
                    ("makeup", "Make-up"),
                ],
                default="excused",
                max_length=16,
            ),
        ),
        migrations.AddConstraint(
            model_name="lessonassignment",
            constraint=models.UniqueConstraint(
                fields=("occurrence", "person", "role"),
                name="unique_lesson_occurrence_person_role_assignment",
            ),
        ),
    ]
