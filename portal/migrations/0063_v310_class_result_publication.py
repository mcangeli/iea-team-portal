from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0062_v310_show_class_live_state"),
    ]

    operations = [
        migrations.AddField(
            model_name="showclasslivestate",
            name="results_published",
            field=models.BooleanField(
                default=False,
                help_text="Publishes finalized placings for this class when public show results are enabled.",
            ),
        ),
    ]
