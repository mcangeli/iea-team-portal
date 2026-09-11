from django.db import migrations, models
import django.db.models.deletion


def migrate_single_show_links(apps, schema_editor):
    FinancialTransaction = apps.get_model("portal", "FinancialTransaction")
    ShowTransactionAllocation = apps.get_model("portal", "ShowTransactionAllocation")
    for tx in FinancialTransaction.objects.exclude(show_id=None).exclude(show_finance_scope="").iterator():
        ShowTransactionAllocation.objects.get_or_create(
            transaction_id=tx.pk,
            show_id=tx.show_id,
            scope=tx.show_finance_scope,
            defaults={"amount": tx.amount, "notes": "Migrated from v1.9.4.1 single-show transaction"},
        )


def reverse_single_show_links(apps, schema_editor):
    # Keep legacy transaction show fields intact; only remove generated allocation rows on rollback.
    ShowTransactionAllocation = apps.get_model("portal", "ShowTransactionAllocation")
    ShowTransactionAllocation.objects.filter(
        notes="Migrated from v1.9.4.1 single-show transaction"
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("portal", "0020_v1941_finance_hardening")]

    operations = [
        migrations.CreateModel(
            name="ShowTransactionAllocation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("scope", models.CharField(choices=[("participation", "Our team participation"), ("hosting", "Hosting operations")], max_length=20)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("show", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="financial_allocations", to="portal.show")),
                ("transaction", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="show_allocations", to="portal.financialtransaction")),
            ],
            options={"ordering": ["show__show_date", "show__name", "scope", "id"]},
        ),
        migrations.AddConstraint(
            model_name="showtransactionallocation",
            constraint=models.UniqueConstraint(
                fields=("transaction", "show", "scope"),
                name="unique_transaction_show_scope_allocation",
            ),
        ),
        migrations.AddField(
            model_name="reimbursementrequest",
            name="show_finance_scope",
            field=models.CharField(
                blank=True,
                choices=[("participation", "Our team participation"), ("hosting", "Hosting operations")],
                max_length=20,
            ),
        ),
        migrations.RunPython(migrate_single_show_links, reverse_single_show_links),
    ]
