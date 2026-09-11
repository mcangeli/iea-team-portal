from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0040_v214_show_courses"),
    ]

    operations = [
        migrations.AddField(
            model_name="horseshowassignment",
            name="eligibility_override",
            field=models.BooleanField(default=False, help_text="Coach/Admin approved use outside the horse's season eligibility."),
        ),
        migrations.AddField(
            model_name="horseshowassignment",
            name="eligibility_override_reason",
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
