from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0066_v320_people_foundation"),
    ]

    operations = [
        migrations.CreateModel(
            name="HorsePersonRelationship",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("relationship_type", models.CharField(choices=[("owner", "Owner"), ("boarder", "Boarder / Responsible Party"), ("full_lease", "Full Lease"), ("half_lease", "Half Lease"), ("partial_lease", "Partial Lease"), ("trainer", "Trainer"), ("caretaker", "Caretaker")], max_length=24)),
                ("share_percent", models.PositiveSmallIntegerField(blank=True, help_text="Optional participation share for lease/ownership arrangements, from 1 to 100.", null=True)),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("active", models.BooleanField(default=True)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("horse", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="person_relationships", to="portal.horse")),
                ("person", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="horse_relationships", to="portal.person")),
                ("team", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="horse_person_relationships", to="portal.team")),
            ],
            options={
                "ordering": ["horse__name", "relationship_type", "person__last_name", "person__first_name"],
            },
        ),
        migrations.AddConstraint(
            model_name="horsepersonrelationship",
            constraint=models.UniqueConstraint(fields=("horse", "person", "relationship_type", "start_date"), name="unique_horse_person_relationship_period"),
        ),
    ]
