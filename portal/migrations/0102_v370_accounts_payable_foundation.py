# Generated for ArenaLine v3.7.0 accounts payable foundation.
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("portal", "0101_v362_iea_roster_configured")]

    operations = [
        migrations.CreateModel(
            name="PayableParty",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=180)),
                ("finance_domain", models.CharField(choices=[("general", "General barn"), ("iea", "IEA")], default="general", max_length=12)),
                ("party_type", models.CharField(choices=[("vendor", "Vendor"), ("person", "Person"), ("other", "Other")], default="vendor", max_length=12)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("phone", models.CharField(blank=True, max_length=40)),
                ("active", models.BooleanField(default=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("contact_person", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="payable_party_contacts", to="portal.person")),
                ("team", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="payable_parties", to="portal.team")),
            ],
            options={"ordering": ["name", "id"]},
        ),
        migrations.AddConstraint(model_name="payableparty", constraint=models.UniqueConstraint(fields=("team", "finance_domain", "name"), name="unique_payable_party_team_domain_name")),
        migrations.CreateModel(
            name="PayableObligation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("description", models.CharField(max_length=220)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("obligation_date", models.DateField()),
                ("due_date", models.DateField(blank=True, null=True)),
                ("reference", models.CharField(blank=True, max_length=120)),
                ("status", models.CharField(choices=[("open", "Open"), ("void", "Void")], default="open", max_length=12)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("expense_category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payable_obligations", to="portal.financialcategory")),
                ("party", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="obligations", to="portal.payableparty")),
                ("season", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="payable_obligations", to="portal.season")),
            ],
            options={"ordering": ["due_date", "obligation_date", "id"]},
        ),
        migrations.AddConstraint(model_name="payableobligation", constraint=models.CheckConstraint(condition=models.Q(("amount__gt", 0)), name="payable_obligation_amount_gt_zero")),
        migrations.CreateModel(
            name="PayablePayment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("paid_date", models.DateField()),
                ("method", models.CharField(blank=True, max_length=40)),
                ("reference", models.CharField(blank=True, max_length=120)),
                ("status", models.CharField(choices=[("posted", "Posted"), ("void", "Void")], default="posted", max_length=12)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("financial_transaction", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="payable_payment", to="portal.financialtransaction")),
                ("obligation", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payments", to="portal.payableobligation")),
                ("payment_account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payable_payments", to="portal.financialaccount")),
            ],
            options={"ordering": ["paid_date", "id"]},
        ),
        migrations.AddConstraint(model_name="payablepayment", constraint=models.CheckConstraint(condition=models.Q(("amount__gt", 0)), name="payable_payment_amount_gt_zero")),
    ]
