from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0100_v362_iea_occurrence_roster"),
    ]

    operations = [
        migrations.AddField(
            model_name="lessonoccurrence",
            name="iea_roster_configured",
            field=models.BooleanField(
                default=False,
                help_text="True when this IEA occurrence uses an explicit occurrence-level roster, including an intentionally empty roster.",
            ),
        ),
    ]
