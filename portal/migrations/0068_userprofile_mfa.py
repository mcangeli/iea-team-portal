from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0067_userprofile_email_verification"),
    ]

    operations = [
        migrations.AddField(model_name="userprofile", name="mfa_enabled", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="userprofile", name="mfa_secret", field=models.CharField(blank=True, max_length=64)),
        migrations.AddField(model_name="userprofile", name="mfa_recovery_codes", field=models.JSONField(blank=True, default=list)),
        migrations.AddField(model_name="userprofile", name="mfa_confirmed_at", field=models.DateTimeField(blank=True, null=True)),
    ]
