from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies=[("portal","0097_v350_bank_reconciliation_foundation")]
    operations=[
        migrations.AlterField(
            model_name="receivablepayment",
            name="financial_transaction",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="receivable_payment",
                to="portal.financialtransaction",
            ),
        ),
    ]
