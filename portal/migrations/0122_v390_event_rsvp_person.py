from django.db import migrations, models
import django.db.models.deletion


def backfill_people(apps, schema_editor):
    EventRSVP = apps.get_model("portal", "EventRSVP")
    LegacyPersonLink = apps.get_model("portal", "LegacyPersonLink")
    person_by_rider = dict(
        LegacyPersonLink.objects.exclude(rider_id=None).values_list("rider_id", "person_id")
    )
    for rsvp in EventRSVP.objects.exclude(rider_id=None).iterator():
        person_id = person_by_rider.get(rsvp.rider_id)
        if person_id:
            EventRSVP.objects.filter(pk=rsvp.pk).update(person_id=person_id)


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0121_v390_show_availability_iea_participant"),
    ]

    operations = [
        migrations.AlterField(
            model_name="eventrsvp",
            name="rider",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="event_rsvps",
                to="portal.rider",
            ),
        ),
        migrations.AddField(
            model_name="eventrsvp",
            name="person",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="event_rsvps",
                to="portal.person",
            ),
        ),
        migrations.RunPython(backfill_people, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="eventrsvp",
            name="unique_event_rider_rsvp",
        ),
        migrations.AddConstraint(
            model_name="eventrsvp",
            constraint=models.UniqueConstraint(
                condition=models.Q(("rider__isnull", False)),
                fields=("event", "rider"),
                name="unique_event_rider_rsvp",
            ),
        ),
        migrations.AddConstraint(
            model_name="eventrsvp",
            constraint=models.UniqueConstraint(
                condition=models.Q(("person__isnull", False)),
                fields=("event", "person"),
                name="unique_event_person_rsvp",
            ),
        ),
    ]
