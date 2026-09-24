from django.db import migrations, models
import django.db.models.deletion


def backfill_people(apps, schema_editor):
    LegacyPersonLink = apps.get_model("portal", "LegacyPersonLink")
    VolunteerLog = apps.get_model("portal", "VolunteerLog")
    person_by_rider = dict(
        LegacyPersonLink.objects.exclude(rider_id=None).values_list("rider_id", "person_id")
    )
    for row in VolunteerLog.objects.exclude(rider_id=None).iterator():
        person_id = person_by_rider.get(row.rider_id)
        if person_id:
            VolunteerLog.objects.filter(pk=row.pk).update(person_id=person_id)


class Migration(migrations.Migration):
    dependencies = [("portal", "0124_v390_event_rsvp_person_ordering")]

    operations = [
        migrations.AlterField(
            model_name="volunteerlog", name="rider",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="volunteer_logs", to="portal.rider"),
        ),
        migrations.AddField(
            model_name="volunteerlog", name="person",
            field=models.ForeignKey(blank=True, help_text="Participant/family account receiving volunteer-hour credit.", null=True, on_delete=django.db.models.deletion.CASCADE, related_name="volunteer_logs", to="portal.person"),
        ),
        migrations.RunPython(backfill_people, migrations.RunPython.noop),
    ]
