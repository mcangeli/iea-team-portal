from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0026_v197_show_day_updates"),
    ]

    operations = [
        migrations.AddField(
            model_name="showclass",
            name="prize_list_time",
            field=models.TimeField(
                blank=True,
                help_text="Baseline time published in the prize list, if one is provided.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="showclass",
            name="estimated_time",
            field=models.TimeField(
                blank=True,
                help_text="Current show-day estimate. This can move without changing the published prize-list time.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="showclass",
            name="schedule_note",
            field=models.CharField(
                blank=True,
                help_text="Short public scheduling note, such as 'after lunch break' or 'Ring 2'.",
                max_length=180,
            ),
        ),
    ]
