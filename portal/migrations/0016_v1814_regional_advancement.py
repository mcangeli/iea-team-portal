from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0015_v189_postseason_competition_tracks"),
    ]

    operations = [
        migrations.AddField(
            model_name="show",
            name="futures_team_place",
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text="Overall Futures team placing at a finals show.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="show",
            name="upper_team_place",
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text="Overall Upper School team placing at a finals show.",
                null=True,
            ),
        ),
    ]
