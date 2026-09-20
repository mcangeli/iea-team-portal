from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0106_v371_horse_person_relationships"),
    ]

    operations = [
        migrations.AddField(
            model_name="receivablecredit",
            name="credit_rule",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="generated_credits",
                to="portal.receivablecreditrule",
            ),
        ),
    ]
