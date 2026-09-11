from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("portal", "0031_v200_team_branding")]

    operations = [
        migrations.AddField(
            model_name="teambranding",
            name="futures_hero_image",
            field=models.ImageField(blank=True, null=True, upload_to="team_branding/", help_text="Wide photograph representing the Futures Team."),
        ),
        migrations.AddField(
            model_name="teambranding",
            name="futures_hero_image_position",
            field=models.CharField(choices=[("20%", "Favor top"), ("50%", "Center"), ("80%", "Favor bottom")], default="50%", max_length=8),
        ),
        migrations.AddField(
            model_name="teambranding",
            name="upper_hero_image",
            field=models.ImageField(blank=True, null=True, upload_to="team_branding/", help_text="Wide photograph representing the Upper Team."),
        ),
        migrations.AddField(
            model_name="teambranding",
            name="upper_hero_image_position",
            field=models.CharField(choices=[("20%", "Favor top"), ("50%", "Center"), ("80%", "Favor bottom")], default="50%", max_length=8),
        ),
    ]
