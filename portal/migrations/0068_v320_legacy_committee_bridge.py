from django.db import migrations, models
import django.db.models.deletion


ROLE_MAP = {
    "upper_parent": ("IEA Program", "Upper Team Parent Committee", "chair"),
    "futures_parent": ("IEA Program", "Futures Team Parent Committee", "chair"),
    "treasurer": ("IEA Program", "IEA Finance Committee", "treasurer"),
    "points_secretary": ("IEA Program", "IEA Points & Records", "secretary"),
}


def backfill_legacy_committee_memberships(apps, schema_editor):
    CommitteeAssignment = apps.get_model("portal", "CommitteeAssignment")
    Person = apps.get_model("portal", "Person")
    OrganizationGroup = apps.get_model("portal", "OrganizationGroup")
    Committee = apps.get_model("portal", "Committee")
    CommitteeMembership = apps.get_model("portal", "CommitteeMembership")

    for assignment in CommitteeAssignment.objects.select_related("season", "user").all().iterator():
        mapping = ROLE_MAP.get(assignment.role)
        if not mapping:
            continue
        person = Person.objects.filter(team_id=assignment.team_id, user_id=assignment.user_id).first()
        if person is None:
            continue

        group_name, committee_name, position = mapping
        group = None
        if group_name:
            group, _ = OrganizationGroup.objects.get_or_create(
                team_id=assignment.team_id,
                name=group_name,
                defaults={
                    "group_type": "program",
                    "description": "IEA program structure mirrored from legacy committee assignments.",
                    "active": True,
                },
            )

        committee, _ = Committee.objects.get_or_create(
            team_id=assignment.team_id,
            group_id=group.id if group else None,
            name=committee_name,
            defaults={"active": True},
        )

        notes = "Mirrored from legacy IEA committee assignment."
        if assignment.notes:
            notes = f"{notes} {assignment.notes}"[:255]

        CommitteeMembership.objects.update_or_create(
            legacy_committee_assignment_id=assignment.id,
            defaults={
                "committee_id": committee.id,
                "person_id": person.id,
                "position": position,
                "start_date": assignment.season.start_date,
                "end_date": assignment.season.end_date,
                "active": assignment.active,
                "notes": notes,
            },
        )


def noop_reverse(apps, schema_editor):
    # Legacy CommitteeAssignment rows remain intact and authoritative, so there
    # is no destructive reverse data operation.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0067_v320_horse_person_relationship"),
    ]

    operations = [
        migrations.AddField(
            model_name="committeemembership",
            name="legacy_committee_assignment",
            field=models.OneToOneField(
                blank=True,
                help_text="Compatibility source when this membership mirrors a legacy IEA committee assignment.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="canonical_membership",
                to="portal.committeeassignment",
            ),
        ),
        migrations.RunPython(backfill_legacy_committee_memberships, noop_reverse),
    ]
