from django.db import migrations, models


def populate_iea_participant(apps, schema_editor):
    ShowEntry = apps.get_model("portal", "ShowEntry")
    IEAParticipant = apps.get_model("portal", "IEAParticipant")
    participant_by_rider = dict(
        IEAParticipant.objects.exclude(legacy_rider_id=None).values_list(
            "legacy_rider_id", "id"
        )
    )
    for entry in ShowEntry.objects.filter(
        iea_participant__isnull=True,
        rider__isnull=False,
    ).iterator():
        participant_id = participant_by_rider.get(entry.rider_id)
        if participant_id:
            ShowEntry.objects.filter(pk=entry.pk).update(
                iea_participant_id=participant_id
            )


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0118_v390_seasonmembership_person_native"),
    ]

    operations = [
        migrations.AlterField(
            model_name="showentry",
            name="rider",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.CASCADE,
                related_name="show_entries",
                to="portal.rider",
            ),
        ),
        migrations.AddField(
            model_name="showentry",
            name="iea_participant",
            field=models.ForeignKey(
                blank=True,
                help_text="Person-native IEA participant identity. Legacy Rider remains during the v3.9 transition.",
                null=True,
                on_delete=models.PROTECT,
                related_name="show_entries",
                to="portal.ieaparticipant",
            ),
        ),
        migrations.RunPython(populate_iea_participant, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="showentry",
            name="unique_rider_show_class_track",
        ),
        migrations.AddConstraint(
            model_name="showentry",
            constraint=models.UniqueConstraint(
                condition=models.Q(("rider__isnull", False)),
                fields=("show_class", "rider", "competition_track"),
                name="unique_rider_show_class_track",
            ),
        ),
        migrations.AddConstraint(
            model_name="showentry",
            constraint=models.UniqueConstraint(
                condition=models.Q(("iea_participant__isnull", False)),
                fields=("show_class", "iea_participant", "competition_track"),
                name="unique_iea_participant_show_class_track",
            ),
        ),
    ]
