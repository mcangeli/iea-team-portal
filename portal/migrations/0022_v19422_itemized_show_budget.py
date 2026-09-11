from django.db import migrations, models
import django.db.models.deletion


def populate_budget_descriptions(apps, schema_editor):
    ShowBudgetLine = apps.get_model("portal", "ShowBudgetLine")
    for line in ShowBudgetLine.objects.select_related("category").filter(description="").iterator():
        line.description = line.category.name
        line.save(update_fields=["description"])


class Migration(migrations.Migration):
    dependencies = [("portal", "0021_v1942_multi_show_allocations")]

    operations = [
        migrations.RemoveConstraint(
            model_name="showbudgetline",
            name="unique_show_budget_scope_category_kind",
        ),
        migrations.RemoveConstraint(
            model_name="showtransactionallocation",
            name="unique_transaction_show_scope_allocation",
        ),
        migrations.AddField(
            model_name="showbudgetline",
            name="description",
            field=models.CharField(
                default="",
                help_text="Specific budget item, such as Insurance, Judge fee, Food, or Facility rental.",
                max_length=160,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="showtransactionallocation",
            name="budget_line",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="transaction_allocations",
                to="portal.showbudgetline",
            ),
        ),
        migrations.RunPython(populate_budget_descriptions, migrations.RunPython.noop),
    ]
