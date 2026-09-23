# Generated for ArenaLine v3.9.0 Preview 2.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0115_v390_organization_group_membership"),
    ]

    operations = [
        migrations.CreateModel(
            name="IEAParticipant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("iea_member_number", models.CharField(blank=True, max_length=40)),
                ("active", models.BooleanField(default=True)),
                ("notes", models.CharField(blank=True, max_length=255)),
                (
                    "legacy_rider",
                    models.OneToOneField(
                        blank=True,
                        help_text="Compatibility source while legacy Rider-backed IEA workflows are migrated.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="iea_participant_bridge",
                        to="portal.rider",
                    ),
                ),
                (
                    "person",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="iea_participant",
                        to="portal.person",
                    ),
                ),
                (
                    "team",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="iea_participants",
                        to="portal.team",
                    ),
                ),
            ],
            options={
                "ordering": ["person__last_name", "person__first_name", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="ieaparticipant",
            constraint=models.UniqueConstraint(
                condition=~models.Q(("iea_member_number", "")),
                fields=("team", "iea_member_number"),
                name="unique_iea_member_number_per_team",
            ),
        ),
    ]
