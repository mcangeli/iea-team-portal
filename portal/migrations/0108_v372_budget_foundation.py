# ArenaLine v3.7.2 generic Barn/IEA budgeting foundation.
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies=[("portal","0107_v371_receivable_credit_rule_traceability")]
    operations=[
        migrations.CreateModel(
            name="Budget",
            fields=[
                ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
                ("finance_domain",models.CharField(choices=[("general","General barn"),("iea","IEA")],default="general",max_length=12)),
                ("name",models.CharField(max_length=180)),
                ("start_date",models.DateField()),
                ("end_date",models.DateField()),
                ("status",models.CharField(choices=[("draft","Draft"),("active","Active"),("closed","Closed")],default="draft",max_length=12)),
                ("notes",models.TextField(blank=True)),
                ("created_at",models.DateTimeField(auto_now_add=True)),
                ("updated_at",models.DateTimeField(auto_now=True)),
                ("season",models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.PROTECT,related_name="finance_budgets",to="portal.season")),
                ("team",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name="finance_budgets",to="portal.team")),
            ],
            options={"ordering":["-start_date","name","id"]},
        ),
        migrations.AddConstraint(model_name="budget",constraint=models.UniqueConstraint(fields=("team","finance_domain","name","start_date","end_date"),name="unique_budget_team_domain_period_name")),
        migrations.CreateModel(
            name="BudgetLine",
            fields=[
                ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
                ("kind",models.CharField(choices=[("income","Income"),("expense","Expense")],default="expense",max_length=20)),
                ("description",models.CharField(max_length=180)),
                ("amount",models.DecimalField(decimal_places=2,default=0,max_digits=12)),
                ("sort_order",models.PositiveIntegerField(default=0)),
                ("notes",models.CharField(blank=True,max_length=255)),
                ("created_at",models.DateTimeField(auto_now_add=True)),
                ("updated_at",models.DateTimeField(auto_now=True)),
                ("budget",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name="lines",to="portal.budget")),
                ("category",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="budget_lines",to="portal.financialcategory")),
            ],
            options={"ordering":["sort_order","category__sort_order","category__name","description","id"]},
        ),
        migrations.AddConstraint(model_name="budgetline",constraint=models.CheckConstraint(condition=models.Q(("amount__gte",0)),name="budget_line_amount_gte_zero")),
        migrations.AddConstraint(model_name="budgetline",constraint=models.UniqueConstraint(fields=("budget","kind","category","description"),name="unique_budget_line_category_description")),
    ]
