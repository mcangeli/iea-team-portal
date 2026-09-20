from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies=[("portal","0104_v371_generated_receivable_credits")]
    operations=[
        migrations.CreateModel(
            name="ReceivableCreditRule",
            fields=[
                ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
                ("finance_domain",models.CharField(choices=[("general","General barn"),("iea","IEA")],default="general",max_length=12)),
                ("name",models.CharField(max_length=160)),
                ("source_type",models.CharField(max_length=60)),
                ("calculation",models.CharField(choices=[("fixed","Fixed amount"),("quantity","Amount per unit")],default="fixed",max_length=16)),
                ("rate",models.DecimalField(decimal_places=2,max_digits=12)),
                ("credit_type",models.CharField(blank=True,max_length=40)),
                ("active",models.BooleanField(default=True)),
                ("notes",models.TextField(blank=True)),
                ("created_at",models.DateTimeField(auto_now_add=True)),
                ("updated_at",models.DateTimeField(auto_now=True)),
                ("team",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name="receivable_credit_rules",to="portal.team")),
            ],
            options={"ordering":["name","id"]},
        ),
        migrations.AddConstraint(model_name="receivablecreditrule",constraint=models.CheckConstraint(condition=models.Q(rate__gt=0),name="receivable_credit_rule_rate_gt_zero")),
    ]
