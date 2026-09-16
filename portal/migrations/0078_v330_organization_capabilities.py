from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0077_v330_horse_compliance_requirements"),
    ]

    operations = [
        migrations.CreateModel(
            name="OrganizationCapabilityAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("capability", models.CharField(choices=[("manage_horses", "Manage Horses")], max_length=40)),
                ("active", models.BooleanField(default=True)),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("person", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="capability_assignments", to="portal.person")),
                ("team", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="capability_assignments", to="portal.team")),
            ],
            options={
                "ordering": ["capability", "person__last_name", "person__first_name"],
            },
        ),
        migrations.AddConstraint(
            model_name="organizationcapabilityassignment",
            constraint=models.UniqueConstraint(fields=("team", "person", "capability"), name="unique_person_organization_capability"),
        ),
    ]
