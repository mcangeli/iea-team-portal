from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0070_v322_person_multi_roles"),
    ]

    operations = [
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
