from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("portal", "0068_userprofile_mfa")]
    operations = [
        migrations.AddField(
            model_name="teambranding",
            name="barn_hero_image",
            field=models.ImageField(blank=True, help_text="Wide barn/program photograph used on the general ArenaLine dashboard.", null=True, upload_to="team_branding/"),
        ),
        migrations.AddField(
            model_name="teambranding",
            name="barn_hero_image_position",
            field=models.CharField(choices=[("20%", "Favor top"), ("50%", "Center"), ("80%", "Favor bottom")], default="50%", help_text="Adjust which part of the barn photograph remains visible when it is cropped.", max_length=8),
        ),
        migrations.AlterField(
            model_name="teambranding",
            name="hero_image",
            field=models.ImageField(blank=True, help_text="Wide IEA team/show photograph used on My Team and the sign-in presentation.", null=True, upload_to="team_branding/"),
        ),
    ]
