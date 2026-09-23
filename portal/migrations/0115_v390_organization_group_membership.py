# Generated for ArenaLine v3.9.0 Preview 2.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0114_inventorytransaction_adjustment_direction"),
    ]

    operations = [
        migrations.CreateModel(
            name="OrganizationGroupMembership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("inactive", "Inactive"),
                            ("pending", "Pending"),
                            ("alumni", "Alumni"),
                        ],
                        default="active",
                        max_length=20,
                    ),
                ),
                (
                    "role_label",
                    models.CharField(
                        blank=True,
                        help_text="Optional program-specific label; this does not grant application permissions.",
                        max_length=80,
                    ),
                ),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("active", models.BooleanField(default=True)),
                ("notes", models.CharField(blank=True, max_length=255)),
                (
                    "group",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="memberships",
                        to="portal.organizationgroup",
                    ),
                ),
                (
                    "person",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="organization_group_memberships",
                        to="portal.person",
                    ),
                ),
                (
                    "team",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="organization_group_memberships",
                        to="portal.team",
                    ),
                ),
            ],
            options={
                "ordering": ["group__sort_order", "group__name", "person__last_name", "person__first_name"],
            },
        ),
        migrations.AddConstraint(
            model_name="organizationgroupmembership",
            constraint=models.UniqueConstraint(
                fields=("group", "person", "start_date"),
                name="unique_group_person_membership_period",
            ),
        ),
        migrations.AddConstraint(
            model_name="organizationgroupmembership",
            constraint=models.UniqueConstraint(
                condition=models.Q(("start_date__isnull", True)),
                fields=("group", "person"),
                name="unique_group_person_membership_null_start",
            ),
        ),
    ]
