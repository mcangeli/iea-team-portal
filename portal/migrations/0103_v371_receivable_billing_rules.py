# ArenaLine v3.7.1 recurring/service-generated receivables foundation.
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies=[("portal","0102_v370_accounts_payable_foundation")]
    operations=[
        migrations.CreateModel(
            name="ReceivableBillingRule",
            fields=[
                ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
                ("description",models.CharField(max_length=220)),
                ("amount",models.DecimalField(decimal_places=2,max_digits=12)),
                ("cadence",models.CharField(choices=[("manual","Manual"),("monthly","Monthly"),("service","Service generated")],default="manual",max_length=16)),
                ("charge_type",models.CharField(blank=True,max_length=40)),
                ("due_days",models.PositiveSmallIntegerField(default=0,help_text="Days after the charge date that payment is due.")),
                ("active",models.BooleanField(default=True)),
                ("notes",models.TextField(blank=True)),
                ("created_at",models.DateTimeField(auto_now_add=True)),
                ("updated_at",models.DateTimeField(auto_now=True)),
                ("account",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="billing_rules",to="portal.receivableaccount")),
            ],
            options={"ordering":["account__name","description","id"]},
        ),
        migrations.AddConstraint(model_name="receivablebillingrule",constraint=models.CheckConstraint(condition=models.Q(("amount__gt",0)),name="receivable_billing_rule_amount_gt_zero")),
        migrations.AddField(model_name="receivablecharge",name="billing_rule",field=models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.PROTECT,related_name="generated_charges",to="portal.receivablebillingrule")),
        migrations.AddField(model_name="receivablecharge",name="generation_key",field=models.CharField(blank=True,max_length=160)),
        migrations.AddConstraint(model_name="receivablecharge",constraint=models.UniqueConstraint(condition=models.Q(("billing_rule__isnull",False),models.Q(("generation_key",""),_negated=True)),fields=("billing_rule","generation_key"),name="unique_receivable_generated_charge")),
    ]
