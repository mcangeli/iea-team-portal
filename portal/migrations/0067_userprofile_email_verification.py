from django.db import migrations, models


def trust_existing_emails(apps, schema_editor):
    UserProfile = apps.get_model("portal", "UserProfile")
    UserProfile.objects.filter(
        user__email__isnull=False,
    ).exclude(user__email="").update(email_verified_at=models.functions.Now())


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0066_lesson_occurrence_horse_assignment"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="email_verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="pending_email",
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="pending_email_requested_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(trust_existing_emails, migrations.RunPython.noop),
    ]
