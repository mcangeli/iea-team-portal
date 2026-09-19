from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("portal", "0099_v350_accounting_export_profiles")]

    operations = [
        migrations.AlterField(
            model_name="iealessonseriescontext",
            name="team_level",
            field=models.CharField(
                choices=[
                    ("futures", "Futures Team"),
                    ("upper", "Upper School Team"),
                    ("mixed", "Mixed Futures + Upper"),
                ],
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="IEALessonOccurrenceParticipant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("occurrence", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="iea_participants", to="portal.lessonoccurrence")),
                ("person", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="iea_lesson_occurrences", to="portal.person")),
            ],
            options={"ordering": ["person__last_name", "person__first_name", "id"]},
        ),
        migrations.AddConstraint(
            model_name="iealessonoccurrenceparticipant",
            constraint=models.UniqueConstraint(fields=("occurrence", "person"), name="unique_iea_occurrence_person"),
        ),
    ]
