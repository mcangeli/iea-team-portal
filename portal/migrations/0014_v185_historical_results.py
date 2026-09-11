from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0013_v182_user_sequence_repair"),
    ]

    operations = [
        migrations.AddField(
            model_name="show",
            name="is_historical_import",
            field=models.BooleanField(
                default=False,
                help_text="Marks a show created through the historical-results workflow.",
            ),
        ),
    ]
