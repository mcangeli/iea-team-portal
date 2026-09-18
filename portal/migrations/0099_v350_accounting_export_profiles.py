from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies=[("portal","0098_alter_receivablepayment_financial_transaction")]
    operations=[
        migrations.CreateModel(
            name="AccountingExportProfile",
            fields=[
                ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
                ("name",models.CharField(max_length=120)),
                ("finance_domain",models.CharField(choices=[("general","General Barn"),("iea","IEA")],max_length=20)),
                ("file_type",models.CharField(choices=[("csv","CSV"),("xlsx","Excel (.xlsx)")],default="csv",max_length=10)),
                ("column_mapping",models.JSONField(blank=True,default=dict)),
                ("active",models.BooleanField(default=True)),
                ("created_at",models.DateTimeField(auto_now_add=True)),
                ("updated_at",models.DateTimeField(auto_now=True)),
                ("team",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name="accounting_export_profiles",to="portal.team")),
            ],
            options={"ordering":("finance_domain","name")},
        ),
        migrations.AddConstraint(model_name="accountingexportprofile",constraint=models.UniqueConstraint(fields=("team","finance_domain","name"),name="uniq_accounting_export_profile_domain_name")),
    ]
