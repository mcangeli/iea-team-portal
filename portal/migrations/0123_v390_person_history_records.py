from django.db import migrations, models
import django.db.models.deletion


def backfill_people(apps, schema_editor):
    LegacyPersonLink = apps.get_model("portal", "LegacyPersonLink")
    RiderDevelopmentNote = apps.get_model("portal", "RiderDevelopmentNote")
    RiderAward = apps.get_model("portal", "RiderAward")
    person_by_rider = dict(
        LegacyPersonLink.objects.exclude(rider_id=None).values_list("rider_id", "person_id")
    )
    for model in (RiderDevelopmentNote, RiderAward):
        for row in model.objects.exclude(rider_id=None).iterator():
            person_id = person_by_rider.get(row.rider_id)
            if person_id:
                model.objects.filter(pk=row.pk).update(person_id=person_id)


class Migration(migrations.Migration):
    dependencies = [("portal", "0122_v390_event_rsvp_person")]

    operations = [
        migrations.AlterField(
            model_name="riderdevelopmentnote", name="rider",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="development_notes", to="portal.rider"),
        ),
        migrations.AddField(
            model_name="riderdevelopmentnote", name="person",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="development_notes", to="portal.person"),
        ),
        migrations.AlterField(
            model_name="rideraward", name="rider",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="awards", to="portal.rider"),
        ),
        migrations.AddField(
            model_name="rideraward", name="person",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="awards", to="portal.person"),
        ),
        migrations.RunPython(backfill_people, migrations.RunPython.noop),
        migrations.RemoveConstraint(model_name="rideraward", name="unique_season_rider_award"),
        migrations.AddConstraint(
            model_name="rideraward",
            constraint=models.UniqueConstraint(condition=models.Q(("rider__isnull", False)), fields=("season", "rider", "title"), name="unique_season_rider_award"),
        ),
        migrations.AddConstraint(
            model_name="rideraward",
            constraint=models.UniqueConstraint(condition=models.Q(("person__isnull", False)), fields=("season", "person", "title"), name="unique_season_person_award"),
        ),
    ]
