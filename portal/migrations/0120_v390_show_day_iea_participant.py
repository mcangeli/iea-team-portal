from django.db import migrations, models
import django.db.models.deletion


def backfill_iea_participants(apps, schema_editor):
    ShowDayRiderStatus = apps.get_model("portal", "ShowDayRiderStatus")
    IEAParticipant = apps.get_model("portal", "IEAParticipant")
    links = {
        p.legacy_rider_id: p.id
        for p in IEAParticipant.objects.exclude(legacy_rider_id=None)
    }
    for status in ShowDayRiderStatus.objects.filter(rider_id__isnull=False, iea_participant_id__isnull=True):
        participant_id = links.get(status.rider_id)
        if participant_id:
            status.iea_participant_id = participant_id
            status.save(update_fields=["iea_participant"])


class Migration(migrations.Migration):
    dependencies = [("portal", "0119_v390_showentry_iea_participant")]

    operations = [
        migrations.AlterField(
            model_name="showdayriderstatus",
            name="rider",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                related_name="show_day_statuses", to="portal.rider",
            ),
        ),
        migrations.AddField(
            model_name="showdayriderstatus",
            name="iea_participant",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                related_name="show_day_statuses", to="portal.ieaparticipant",
            ),
        ),
        migrations.RunPython(backfill_iea_participants, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="showdayriderstatus",
            name="unique_show_day_rider_status",
        ),
        migrations.AddConstraint(
            model_name="showdayriderstatus",
            constraint=models.UniqueConstraint(
                fields=("show", "rider"),
                condition=models.Q(("rider__isnull", False)),
                name="unique_show_day_rider_status",
            ),
        ),
        migrations.AddConstraint(
            model_name="showdayriderstatus",
            constraint=models.UniqueConstraint(
                fields=("show", "iea_participant"),
                condition=models.Q(("iea_participant__isnull", False)),
                name="unique_show_day_iea_participant_status",
            ),
        ),
    ]
