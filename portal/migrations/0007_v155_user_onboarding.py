from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("portal", "0006_v150_team_operations")]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="must_change_password",
            field=models.BooleanField(default=False),
        ),
    ]
