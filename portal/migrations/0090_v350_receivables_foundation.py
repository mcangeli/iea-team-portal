import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("portal", "0089_v340_lesson_model_state_closeout")]

    operations = [
        migrations.CreateModel(
            name="ReceivableAccount",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=180)),
                ("status", models.CharField(choices=[("active", "Active"), ("closed", "Closed")], default="active", max_length=12)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("primary_person", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="primary_receivable_accounts", to="portal.person")),
                ("team", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="receivable_accounts", to="portal.team")),
            ],
            options={"ordering": ["name", "id"]},
        ),
        migrations.CreateModel(
            name="ReceivableCharge",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("description", models.CharField(max_length=220)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("charge_date", models.DateField()),
                ("due_date", models.DateField(blank=True, null=True)),
                ("charge_type", models.CharField(blank=True, max_length=40)),
                ("status", models.CharField(choices=[("posted", "Posted"), ("waived", "Waived"), ("void", "Void")], default="posted", max_length=12)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="charges", to="portal.receivableaccount")),
                ("season", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="receivable_charges", to="portal.season")),
            ],
            options={"ordering": ["charge_date", "id"]},
        ),
        migrations.CreateModel(
            name="ReceivableCredit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("description", models.CharField(max_length=220)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("credit_date", models.DateField()),
                ("credit_type", models.CharField(blank=True, max_length=40)),
                ("status", models.CharField(choices=[("posted", "Posted"), ("void", "Void")], default="posted", max_length=12)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="credits", to="portal.receivableaccount")),
                ("season", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="receivable_credits", to="portal.season")),
            ],
            options={"ordering": ["credit_date", "id"]},
        ),
        migrations.CreateModel(
            name="ReceivablePayment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("received_date", models.DateField()),
                ("method", models.CharField(blank=True, max_length=40)),
                ("reference", models.CharField(blank=True, max_length=120)),
                ("notes", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("posted", "Posted"), ("void", "Void")], default="posted", max_length=12)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payments", to="portal.receivableaccount")),
                ("deposit_account", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="receivable_payments", to="portal.financialaccount")),
                ("financial_transaction", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="receivable_payment", to="portal.financialtransaction")),
                ("income_category", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="receivable_payments", to="portal.financialcategory")),
                ("season", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="receivable_payments", to="portal.season")),
            ],
            options={"ordering": ["received_date", "id"]},
        ),
        migrations.CreateModel(
            name="ReceivableAllocation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("status", models.CharField(choices=[("posted", "Posted"), ("void", "Void")], default="posted", max_length=12)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("charge", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="allocations", to="portal.receivablecharge")),
                ("credit", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="allocations", to="portal.receivablecredit")),
                ("payment", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="allocations", to="portal.receivablepayment")),
            ],
            options={"ordering": ["created_at", "id"]},
        ),
        migrations.AddConstraint(model_name="receivableaccount", constraint=models.UniqueConstraint(fields=("team", "name"), name="unique_receivable_account_team_name")),
        migrations.AddConstraint(model_name="receivablecharge", constraint=models.CheckConstraint(condition=models.Q(("amount__gt", 0)), name="receivable_charge_amount_gt_zero")),
        migrations.AddConstraint(model_name="receivablecredit", constraint=models.CheckConstraint(condition=models.Q(("amount__gt", 0)), name="receivable_credit_amount_gt_zero")),
        migrations.AddConstraint(model_name="receivablepayment", constraint=models.CheckConstraint(condition=models.Q(("amount__gt", 0)), name="receivable_payment_amount_gt_zero")),
        migrations.AddConstraint(model_name="receivableallocation", constraint=models.CheckConstraint(condition=models.Q(("amount__gt", 0)), name="receivable_allocation_amount_gt_zero")),
        migrations.AddConstraint(model_name="receivableallocation", constraint=models.CheckConstraint(condition=models.Q(models.Q(("credit__isnull", True), ("payment__isnull", False)), models.Q(("credit__isnull", False), ("payment__isnull", True)), _connector="OR"), name="receivable_allocation_exactly_one_source")),
    ]
