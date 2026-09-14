from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0057_v310_publication_foundation"),
    ]

    operations = [
        migrations.AddField(
            model_name="publicshowpublication",
            name="publish_schedule",
            field=models.BooleanField(
                default=False,
                help_text="Publishes only the show's allow-listed class order and public schedule fields. Entries and internal strategy remain private.",
            ),
        ),
    ]
