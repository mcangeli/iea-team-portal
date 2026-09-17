from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies=[("portal","0095_v350_receivable_account_people")]
    operations=[
        migrations.AlterField(
            model_name="financialtransaction",
            name="season",
            field=models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.PROTECT,related_name="financial_transactions",to="portal.season"),
        ),
    ]
