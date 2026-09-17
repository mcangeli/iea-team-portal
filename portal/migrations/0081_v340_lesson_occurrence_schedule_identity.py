from django.db import migrations, models


def backfill_occurrence_identity(apps, schema_editor):
    LessonOccurrence = apps.get_model("portal", "LessonOccurrence")
    # Existing v3.4 rows include generated schedule materializations and explicit
    # legacy conversions. Legacy-converted occurrences can be recognized by their
    # IEA program description; everything else predating this field came from the
    # recurring generator or explicit/manual work. We only assign recurrence slots
    # where the old row is still a scheduled occurrence created by the generator's
    # exact series weekday/time. This avoids inventing recurrence identity for
    # converted historical data.
    for occurrence in LessonOccurrence.objects.select_related("series", "series__program").all():
        program_description = occurrence.series.program.description or ""
        if "legacy lesson workflow" in program_description:
            occurrence.origin = "legacy"
            occurrence.scheduled_for = None
        elif (
            occurrence.series.weekday is not None
            and occurrence.series.starts_at_time is not None
            and occurrence.starts_at.weekday() == occurrence.series.weekday
            and occurrence.starts_at.timetz().replace(tzinfo=None) == occurrence.series.starts_at_time
        ):
            occurrence.origin = "generated"
            occurrence.scheduled_for = occurrence.starts_at
        else:
            occurrence.origin = "manual"
            occurrence.scheduled_for = None
        occurrence.save(update_fields=["origin", "scheduled_for"])


class Migration(migrations.Migration):
    dependencies = [("portal", "0080_v340_iea_lesson_series_context")]

    operations = [
        migrations.AddField(
            model_name="lessonoccurrence",
            name="origin",
            field=models.CharField(
                choices=[("generated", "Generated"), ("manual", "Manual"), ("legacy", "Legacy conversion")],
                default="manual",
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name="lessonoccurrence",
            name="scheduled_for",
            field=models.DateTimeField(blank=True, help_text="Immutable recurrence slot for generated occurrences.", null=True),
        ),
        migrations.RunPython(backfill_occurrence_identity, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="lessonoccurrence",
            constraint=models.UniqueConstraint(fields=("series", "scheduled_for"), name="unique_lesson_series_scheduled_slot"),
        ),
    ]
