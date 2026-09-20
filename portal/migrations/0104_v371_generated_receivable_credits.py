from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies=[("portal","0103_v371_receivable_billing_rules")]
    operations=[
        migrations.AddField(model_name="receivablecredit",name="generation_key",field=models.CharField(blank=True,max_length=160)),
        migrations.AddField(model_name="receivablecredit",name="source_type",field=models.CharField(blank=True,max_length=60)),
        migrations.AddField(model_name="receivablecredit",name="source_id",field=models.CharField(blank=True,max_length=120)),
        migrations.AddConstraint(model_name="receivablecredit",constraint=models.UniqueConstraint(condition=~models.Q(generation_key=""),fields=("account","generation_key"),name="unique_receivable_generated_credit")),
    ]
