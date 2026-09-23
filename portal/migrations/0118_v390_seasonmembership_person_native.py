from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0117_v390_seasonmembership_iea_participant"),
    ]

    operations = [
        migrations.AlterField(
            model_name="seasonmembership",
            name="rider",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.CASCADE,
                related_name="memberships",
                to="portal.rider",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="seasonmembership",
            name="unique_rider_season",
        ),
        migrations.AddConstraint(
            model_name="seasonmembership",
            constraint=models.UniqueConstraint(
                condition=models.Q(("rider__isnull", False)),
                fields=("rider", "season"),
                name="unique_rider_season",
            ),
        ),
    ]
