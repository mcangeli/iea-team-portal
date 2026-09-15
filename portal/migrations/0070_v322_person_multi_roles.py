from django.db import migrations, models


def backfill_parent_guardian_roles(apps, schema_editor):
    PersonRelationship = apps.get_model("portal", "PersonRelationship")
    OrganizationRoleAssignment = apps.get_model("portal", "OrganizationRoleAssignment")

    parent_person_ids = (
        PersonRelationship.objects.filter(
            relationship_type="parent_guardian",
            active=True,
        )
        .values_list("from_person_id", flat=True)
        .distinct()
    )
    for person_id in parent_person_ids.iterator():
        relationship = (
            PersonRelationship.objects.filter(
                from_person_id=person_id,
                relationship_type="parent_guardian",
                active=True,
            )
            .select_related("from_person")
            .first()
        )
        if relationship is None:
            continue
        OrganizationRoleAssignment.objects.get_or_create(
            team_id=relationship.from_person.team_id,
            person_id=person_id,
            role="parent_guardian",
            start_date=None,
            defaults={"active": True},
        )


def noop_reverse(apps, schema_editor):
    # Parent/Guardian role records represent useful canonical participation and
    # are intentionally retained if this migration is reversed.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0069_v322_station_foundation"),
    ]

    operations = [
        migrations.AlterField(
            model_name="organizationroleassignment",
            name="role",
            field=models.CharField(
                choices=[
                    ("parent_guardian", "Parent / Guardian"),
                    ("rider", "Rider"),
                    ("boarder", "Boarder"),
                    ("trainer", "Trainer"),
                    ("assistant_trainer", "Assistant Trainer"),
                    ("barn_manager", "Barn Manager"),
                    ("barn_staff", "Barn Staff"),
                    ("working_student", "Working Student"),
                    ("board_member", "Board Member"),
                ],
                max_length=30,
            ),
        ),
        migrations.RunPython(backfill_parent_guardian_roles, noop_reverse),
    ]
