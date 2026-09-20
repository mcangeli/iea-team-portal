# ArenaLine v3.7.2 keeps actuals unambiguous at category/kind granularity.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies=[("portal","0108_v372_budget_foundation")]
    operations=[
        migrations.RemoveConstraint(model_name="budgetline",name="unique_budget_line_category_description"),
        migrations.AddConstraint(
            model_name="budgetline",
            constraint=models.UniqueConstraint(fields=("budget","kind","category"),name="unique_budget_line_category_kind"),
        ),
    ]
