from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0028_v197_show_day_checkin"),
    ]

    operations = [
        migrations.AddField(
            model_name="showplanningitem",
            name="item_type",
            field=models.CharField(
                choices=[
                    ("checklist", "Checklist"),
                    ("volunteer", "Volunteer"),
                    ("supply", "Supply / Hospitality"),
                ],
                default="checklist",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="showplanningitem",
            name="team_level",
            field=models.CharField(
                choices=[
                    ("all", "Everyone"),
                    ("futures", "Futures Team"),
                    ("upper", "Upper School Team"),
                ],
                default="all",
                max_length=20,
            ),
        ),
    ]
