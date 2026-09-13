from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0051_v300_iea_season_catalog_configuration"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="seasonclass",
            name="unique_season_class_by_team",
        ),
        migrations.AddConstraint(
            model_name="seasonclass",
            constraint=models.UniqueConstraint(
                fields=("season", "discipline", "name", "team_level"),
                name="unique_season_class_by_team",
            ),
        ),
    ]
