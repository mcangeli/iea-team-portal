from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("portal", "0018_v191_family_finance")]

    operations = [
        migrations.AddField(model_name="season", name="regular_show_fee_policy", field=models.CharField(choices=[("included","Included in membership dues"),("family","Bill families per show"),("package","Season show package"),("manual","Manual / mixed")], default="manual", max_length=20)),
        migrations.AddField(model_name="season", name="regional_show_fee_policy", field=models.CharField(choices=[("included","Included in membership dues"),("family","Bill families per show"),("package","Season show package"),("manual","Manual / mixed")], default="manual", max_length=20)),
        migrations.AddField(model_name="season", name="zone_show_fee_policy", field=models.CharField(choices=[("included","Included in membership dues"),("family","Bill families per show"),("package","Season show package"),("manual","Manual / mixed")], default="manual", max_length=20)),
        migrations.AddField(model_name="season", name="national_show_fee_policy", field=models.CharField(choices=[("included","Included in membership dues"),("family","Bill families per show"),("package","Season show package"),("manual","Manual / mixed")], default="manual", max_length=20)),
        migrations.AddField(model_name="season", name="other_show_fee_policy", field=models.CharField(choices=[("included","Included in membership dues"),("family","Bill families per show"),("package","Season show package"),("manual","Manual / mixed")], default="manual", max_length=20)),
        migrations.AddField(model_name="season", name="default_rider_show_fee", field=models.DecimalField(decimal_places=2, default=0, max_digits=10)),
        migrations.AddField(model_name="season", name="dues_coverage_notes", field=models.TextField(blank=True, help_text="Describe what membership dues or season packages cover.")),
        migrations.AddField(model_name="show", name="financial_role", field=models.CharField(choices=[("attending","Attending"),("hosting_attending","Hosting & attending")], default="attending", max_length=30)),
        migrations.AlterField(model_name="financialtransaction", name="receipt", field=models.FileField(blank=True, null=True, upload_to="finance/private/receipts/%Y/%m/")),
        migrations.CreateModel(
            name="ShowBudgetLine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("scope", models.CharField(choices=[("participation","Our team participation"),("hosting","Hosting operations")], default="participation", max_length=20)),
                ("kind", models.CharField(choices=[("income","Income"),("expense","Expense")], default="expense", max_length=20)),
                ("amount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="show_budget_lines", to="portal.financialcategory")),
                ("show", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="show_budget_lines", to="portal.show")),
            ],
            options={"ordering":["scope","kind","category__sort_order","category__name"]},
        ),
        migrations.AddConstraint(model_name="showbudgetline", constraint=models.UniqueConstraint(fields=("show","scope","category","kind"), name="unique_show_budget_scope_category_kind")),
        migrations.CreateModel(
            name="ReimbursementRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("payee_name", models.CharField(max_length=160)),
                ("expense_date", models.DateField()),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("description", models.CharField(max_length=255)),
                ("receipt", models.FileField(blank=True, null=True, upload_to="finance/private/reimbursements/%Y/%m/")),
                ("status", models.CharField(choices=[("draft","Draft"),("submitted","Submitted"),("approved","Approved"),("rejected","Rejected"),("paid","Paid")], default="draft", max_length=20)),
                ("submitted_at", models.DateTimeField(blank=True, null=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("rejection_reason", models.TextField(blank=True)),
                ("paid_date", models.DateField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="reimbursement_requests", to="portal.financialcategory")),
                ("financial_transaction", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reimbursement_request", to="portal.financialtransaction")),
                ("payment_account", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="reimbursements_paid", to="portal.financialaccount")),
                ("requested_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="reimbursement_requests", to="auth.user")),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reimbursements_reviewed", to="auth.user")),
                ("season", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="reimbursement_requests", to="portal.season")),
                ("show", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reimbursement_requests", to="portal.show")),
                ("team", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reimbursement_requests", to="portal.team")),
            ],
            options={"ordering":["-created_at"]},
        ),
    ]
