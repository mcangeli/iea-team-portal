# Generated for ArenaLine v3.9.0 Preview 2 — SeasonMembership transition.

import django.db.models.deletion
from django.db import migrations, models


def populate_iea_participant(apps, schema_editor):
    SeasonMembership = apps.get_model("portal", "SeasonMembership")
    LegacyPersonLink = apps.get_model("portal", "LegacyPersonLink")
    IEAParticipant = apps.get_model("portal", "IEAParticipant")

    person_by_rider = dict(
        LegacyPersonLink.objects.exclude(rider_id=None).values_list("rider_id", "person_id")
    )
    participant_by_person = dict(
        IEAParticipant.objects.values_list("person_id", "id")
    )

    for membership in SeasonMembership.objects.filter(iea_participant_id=None).iterator():
        person_id = person_by_rider.get(membership.rider_id)
        participant_id = participant_by_person.get(person_id)
        if participant_id is not None:
            SeasonMembership.objects.filter(pk=membership.pk).update(
                iea_participant_id=participant_id
            )


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0116_v390_iea_participant"),
    ]

    operations = [
        migrations.AddField(
            model_name="seasonmembership",
            name="iea_participant",
            field=models.ForeignKey(
                blank=True,
                help_text="Person-native IEA participant identity. Legacy Rider remains during the v3.9 transition.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="season_memberships",
                to="portal.ieaparticipant",
            ),
        ),
        migrations.RunPython(populate_iea_participant, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="seasonmembership",
            constraint=models.UniqueConstraint(
                condition=models.Q(("iea_participant__isnull", False)),
                fields=("iea_participant", "season"),
                name="unique_iea_participant_season",
            ),
        ),
    ]
