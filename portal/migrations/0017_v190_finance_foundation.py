from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def seed_finance_categories(apps, schema_editor):
    Team = apps.get_model("portal", "Team")
    FinancialCategory = apps.get_model("portal", "FinancialCategory")
    defaults = [
        ("Membership dues", "income", 10),
        ("Fundraising", "income", 20),
        ("Show fees", "both", 30),
        ("Coaching", "expense", 40),
        ("Facility / barn", "expense", 50),
        ("Horse rental", "expense", 60),
        ("Apparel", "both", 70),
        ("Travel", "expense", 80),
        ("Awards / banquet", "expense", 90),
        ("Administrative", "expense", 100),
        ("Miscellaneous", "both", 110),
    ]
    for team in Team.objects.all():
        for name, kind, sort_order in defaults:
            FinancialCategory.objects.get_or_create(
                team=team, name=name,
                defaults={"kind": kind, "sort_order": sort_order, "active": True},
            )


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0016_v1814_regional_advancement"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="FinancialAccount",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("account_type", models.CharField(choices=[("checking","Checking"),("savings","Savings"),("cash","Cash"),("clearing","Payment / clearing"),("other","Other")], default="checking", max_length=20)),
                ("opening_balance", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("active", models.BooleanField(default=True)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("team", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="financial_accounts", to="portal.team")),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="FinancialCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("kind", models.CharField(choices=[("income","Income"),("expense","Expense"),("both","Income or expense")], default="expense", max_length=20)),
                ("active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("team", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="financial_categories", to="portal.team")),
            ],
            options={"ordering": ["sort_order", "name"]},
        ),
        migrations.CreateModel(
            name="FinancialTransaction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("transaction_date", models.DateField()),
                ("kind", models.CharField(choices=[("income","Income"),("expense","Expense")], max_length=20)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("payee", models.CharField(blank=True, max_length=160)),
                ("description", models.CharField(max_length=255)),
                ("receipt", models.FileField(blank=True, null=True, upload_to="finance/receipts/%Y/%m/")),
                ("reference", models.CharField(blank=True, help_text="Optional check number, payment reference, or external transaction ID.", max_length=100)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="transactions", to="portal.financialaccount")),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="transactions", to="portal.financialcategory")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="financial_transactions_created", to=settings.AUTH_USER_MODEL)),
                ("rider", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="financial_transactions", to="portal.rider")),
                ("season", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="financial_transactions", to="portal.season")),
                ("show", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="financial_transactions", to="portal.show")),
                ("team", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="financial_transactions", to="portal.team")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="financial_transactions_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-transaction_date", "-created_at"]},
        ),
        migrations.CreateModel(
            name="SeasonBudget",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("income","Income"),("expense","Expense")], default="expense", max_length=20)),
                ("amount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="season_budgets", to="portal.financialcategory")),
                ("season", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="budgets", to="portal.season")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="season_budgets_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["category__sort_order", "category__name"]},
        ),
        migrations.AddConstraint(
            model_name="financialaccount",
            constraint=models.UniqueConstraint(fields=("team", "name"), name="unique_financial_account_team_name"),
        ),
        migrations.AddConstraint(
            model_name="financialcategory",
            constraint=models.UniqueConstraint(fields=("team", "name"), name="unique_financial_category_team_name"),
        ),
        migrations.AddConstraint(
            model_name="seasonbudget",
            constraint=models.UniqueConstraint(fields=("season", "category", "kind"), name="unique_season_budget_category_kind"),
        ),
        migrations.RunPython(seed_finance_categories, migrations.RunPython.noop),
    ]
