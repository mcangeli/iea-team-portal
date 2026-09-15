from django.db import migrations, models
from django.db.models import Count


def _merge_notes(rows, max_length=255):
    values = []
    for row in rows:
        value = (getattr(row, "notes", "") or "").strip()
        if value and value not in values:
            values.append(value)
    return "; ".join(values)[:max_length]


def _dedupe_null_start_rows(Model, group_fields, *, prefer_legacy=False):
    duplicate_groups = (
        Model.objects.filter(start_date__isnull=True)
        .values(*group_fields)
        .annotate(row_count=Count("id"))
        .filter(row_count__gt=1)
    )
    for group in duplicate_groups.iterator():
        filters = {field: group[field] for field in group_fields}
        rows = list(Model.objects.filter(start_date__isnull=True, **filters).order_by("id"))
        if len(rows) < 2:
            continue

        if prefer_legacy:
            rows.sort(
                key=lambda row: (
                    0 if getattr(row, "legacy_committee_assignment_id", None) else 1,
                    0 if getattr(row, "active", False) else 1,
                    row.id,
                )
            )
        else:
            rows.sort(key=lambda row: (0 if getattr(row, "active", False) else 1, row.id))

        keeper = rows[0]
        duplicates = rows[1:]
        all_rows = [keeper, *duplicates]
        keeper.active = any(getattr(row, "active", False) for row in all_rows)
        if keeper.active:
            keeper.end_date = None
        else:
            end_dates = [row.end_date for row in all_rows if getattr(row, "end_date", None)]
            keeper.end_date = max(end_dates) if end_dates else None
        keeper.notes = _merge_notes(all_rows)

        if hasattr(keeper, "share_percent") and keeper.share_percent is None:
            keeper.share_percent = next(
                (row.share_percent for row in all_rows if row.share_percent is not None),
                None,
            )
        if prefer_legacy and not getattr(keeper, "legacy_committee_assignment_id", None):
            keeper.legacy_committee_assignment_id = next(
                (
                    row.legacy_committee_assignment_id
                    for row in all_rows
                    if getattr(row, "legacy_committee_assignment_id", None)
                ),
                None,
            )

        keeper.save()
        Model.objects.filter(pk__in=[row.pk for row in duplicates]).delete()


def _merge_committee_membership(target, source):
    rows = [target, source]
    target.active = target.active or source.active
    if target.active:
        target.end_date = None
    else:
        end_dates = [row.end_date for row in rows if row.end_date]
        target.end_date = max(end_dates) if end_dates else None
    target.notes = _merge_notes(rows)
    if not target.legacy_committee_assignment_id and source.legacy_committee_assignment_id:
        target.legacy_committee_assignment_id = source.legacy_committee_assignment_id
    target.save()
    source.delete()


def consolidate_preview_duplicates(apps, schema_editor):
    OrganizationRoleAssignment = apps.get_model("portal", "OrganizationRoleAssignment")
    Committee = apps.get_model("portal", "Committee")
    CommitteeMembership = apps.get_model("portal", "CommitteeMembership")
    HorsePersonRelationship = apps.get_model("portal", "HorsePersonRelationship")

    _dedupe_null_start_rows(
        OrganizationRoleAssignment,
        ["team_id", "person_id", "role"],
    )
    _dedupe_null_start_rows(
        HorsePersonRelationship,
        ["horse_id", "person_id", "relationship_type"],
    )

    duplicate_committees = (
        Committee.objects.filter(group__isnull=True)
        .values("team_id", "name")
        .annotate(row_count=Count("id"))
        .filter(row_count__gt=1)
    )
    for group in duplicate_committees.iterator():
        committees = list(
            Committee.objects.filter(
                team_id=group["team_id"],
                name=group["name"],
                group__isnull=True,
            ).order_by("id")
        )
        if len(committees) < 2:
            continue
        keeper = committees[0]
        duplicates = committees[1:]

        purposes = []
        for committee in committees:
            purpose = (committee.purpose or "").strip()
            if purpose and purpose not in purposes:
                purposes.append(purpose)
        keeper.purpose = "\n\n".join(purposes)
        keeper.active = any(committee.active for committee in committees)
        keeper.sort_order = min(committee.sort_order for committee in committees)
        keeper.save(update_fields=["purpose", "active", "sort_order"])

        for duplicate in duplicates:
            memberships = list(CommitteeMembership.objects.filter(committee_id=duplicate.pk).order_by("id"))
            for membership in memberships:
                existing = CommitteeMembership.objects.filter(
                    committee_id=keeper.pk,
                    person_id=membership.person_id,
                    position=membership.position,
                    start_date=membership.start_date,
                ).order_by("id").first()
                if existing:
                    _merge_committee_membership(existing, membership)
                else:
                    membership.committee_id = keeper.pk
                    membership.save(update_fields=["committee"])
            duplicate.delete()

    _dedupe_null_start_rows(
        CommitteeMembership,
        ["committee_id", "person_id", "position"],
        prefer_legacy=True,
    )


def noop_reverse(apps, schema_editor):
    # Consolidated duplicate preview rows are intentionally not recreated.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0070_v322_person_multi_roles"),
    ]

    operations = [
        migrations.RunPython(consolidate_preview_duplicates, noop_reverse),
        migrations.AddConstraint(
            model_name="organizationroleassignment",
            constraint=models.UniqueConstraint(
                fields=("team", "person", "role"),
                condition=models.Q(("start_date__isnull", True)),
                name="unique_person_role_assignment_null_start",
            ),
        ),
        migrations.AddConstraint(
            model_name="committee",
            constraint=models.UniqueConstraint(
                fields=("team", "name"),
                condition=models.Q(("group__isnull", True)),
                name="unique_barnwide_committee_name",
            ),
        ),
        migrations.AddConstraint(
            model_name="committeemembership",
            constraint=models.UniqueConstraint(
                fields=("committee", "person", "position"),
                condition=models.Q(("start_date__isnull", True)),
                name="unique_committee_membership_null_start",
            ),
        ),
        migrations.AddConstraint(
            model_name="horsepersonrelationship",
            constraint=models.UniqueConstraint(
                fields=("horse", "person", "relationship_type"),
                condition=models.Q(("start_date__isnull", True)),
                name="unique_horse_person_relationship_null_start",
            ),
        ),
    ]
