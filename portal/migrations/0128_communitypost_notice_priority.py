from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("portal", "0127_communitypost_communitypostaudience")]
    operations = [
        migrations.AddField(model_name="communitypost", name="is_notice", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="communitypost", name="notice_until", field=models.DateTimeField(blank=True, null=True)),
    ]
