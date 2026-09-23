from django.db import migrations, models
import django.db.models.deletion


def backfill_iea_participants(apps, schema_editor):
    ShowAvailability = apps.get_model("portal", "ShowAvailability")
    IEAParticipant = apps.get_model("portal", "IEAParticipant")
    participant_by_rider = dict(
        IEAParticipant.objects.exclude(legacy_rider_id=None).values_list("legacy_rider_id", "id")
    )
    for availability in ShowAvailability.objects.exclude(rider_id=None).iterator():
        participant_id = participant_by_rider.get(availability.rider_id)
        if participant_id:
            ShowAvailability.objects.filter(pk=availability.pk).update(
                iea_participant_id=participant_id
            )


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0120_v390_show_day_iea_participant"),
    ]

    operations = [
        migrations.AlterField(
            model_name="showavailability",
            name="rider",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="show_availability",
                to="portal.rider",
            ),
        ),
        migrations.AddField(
            model_name="showavailability",
            name="iea_participant",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="show_availability",
                to="portal.ieaparticipant",
            ),
        ),
        migrations.RunPython(backfill_iea_participants, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="showavailability",
            name="unique_show_rider_availability",
        ),
        migrations.AddConstraint(
            model_name="showavailability",
            constraint=models.UniqueConstraint(
                condition=models.Q(("rider__isnull", False)),
                fields=("show", "rider"),
                name="unique_show_rider_availability",
            ),
        ),
        migrations.AddConstraint(
            model_name="showavailability",
            constraint=models.UniqueConstraint(
                condition=models.Q(("iea_participant__isnull", False)),
                fields=("show", "iea_participant"),
                name="unique_show_iea_participant_availability",
            ),
        ),
    ]
