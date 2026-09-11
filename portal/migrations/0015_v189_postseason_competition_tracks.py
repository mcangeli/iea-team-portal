from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0014_v185_historical_results"),
    ]

    operations = [
        migrations.AddField(
            model_name="show",
            name="competition_level",
            field=models.CharField(
                choices=[
                    ("regular", "Regular season"),
                    ("regional", "Region Finals"),
                    ("zone", "Zone Finals"),
                    ("national", "National Finals"),
                ],
                default="regular",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="showentry",
            name="competition_track",
            field=models.CharField(
                choices=[
                    ("regular", "Regular-season entry"),
                    ("individual", "Individual finals"),
                    ("team", "Team finals"),
                ],
                default="regular",
                max_length=20,
            ),
        ),
        migrations.RemoveConstraint(
            model_name="showentry",
            name="unique_rider_show_class",
        ),
        migrations.AddConstraint(
            model_name="showentry",
            constraint=models.UniqueConstraint(
                fields=("show_class", "rider", "competition_track"),
                name="unique_rider_show_class_track",
            ),
        ),
    ]
