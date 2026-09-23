from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("portal", "0123_v390_person_history_records")]

    operations = [
        migrations.AlterModelOptions(
            name="eventrsvp",
            options={
                "ordering": [
                    "person__last_name",
                    "person__first_name",
                    "rider__last_name",
                    "rider__first_name",
                ]
            },
        ),
    ]
