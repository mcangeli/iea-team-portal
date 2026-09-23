from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0111_facility_facilityspace_horsepastureassignment_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="resourcereservation",
            name="cancelled_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
