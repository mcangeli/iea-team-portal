from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0058_v310_public_show_schedule"),
    ]

    operations = [
        migrations.AddField(
            model_name="publicshowpublication",
            name="publish_results",
            field=models.BooleanField(
                default=False,
                help_text="Publishes only finalized class placings and rider display names. Entry strategy, internal notes, and points-rider status remain private.",
            ),
        ),
    ]
