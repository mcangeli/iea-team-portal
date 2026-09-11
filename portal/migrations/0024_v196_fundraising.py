from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0023_v195_operational_audit"),
    ]

    operations = [
        migrations.AlterField(
            model_name="familycredit",
            name="credit_type",
            field=models.CharField(
                choices=[
                    ("scholarship", "Scholarship / aid"),
                    ("courtesy", "Courtesy credit"),
                    ("manual", "Manual adjustment"),
                    ("fundraising", "Fundraising credit"),
                    ("other", "Other"),
                ],
                default="manual",
                max_length=30,
            ),
        ),
        migrations.CreateModel(
            name="FundraisingCampaign",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=180)),
                ("description", models.TextField(blank=True)),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("goal_amount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("status", models.CharField(choices=[("planned", "Planned"), ("active", "Active"), ("closed", "Closed")], default="planned", max_length=20)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="fundraising_campaigns_created", to=settings.AUTH_USER_MODEL)),
                ("season", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="fundraising_campaigns", to="portal.season")),
                ("team", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="fundraising_campaigns", to="portal.team")),
            ],
            options={"ordering": ["-start_date", "-created_at", "name"]},
        ),
        migrations.CreateModel(
            name="FundraisingContribution",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("received_date", models.DateField(default=django.utils.timezone.localdate)),
                ("donor_name", models.CharField(blank=True, max_length=180)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("family_credit_amount", models.DecimalField(decimal_places=2, default=0, help_text="Optional portion credited to the attributed family's receivable balance.", max_digits=12)),
                ("method", models.CharField(blank=True, max_length=80)),
                ("reference", models.CharField(blank=True, max_length=120)),
                ("notes", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("posted", "Posted"), ("void", "Void")], default="posted", max_length=12)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("voided_at", models.DateTimeField(blank=True, null=True)),
                ("void_reason", models.CharField(blank=True, max_length=255)),
                ("account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="fundraising_contributions", to="portal.financialaccount")),
                ("beneficiary_membership", models.ForeignKey(blank=True, help_text="Optional rider/family attribution for this contribution.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="fundraising_contributions", to="portal.seasonmembership")),
                ("campaign", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="contributions", to="portal.fundraisingcampaign")),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="fundraising_contributions", to="portal.financialcategory")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="fundraising_contributions_created", to=settings.AUTH_USER_MODEL)),
                ("family_charge", models.ForeignKey(blank=True, help_text="Required when a family credit is applied; choose the family charge to reduce.", null=True, on_delete=django.db.models.deletion.PROTECT, related_name="fundraising_contributions", to="portal.familycharge")),
                ("family_credit", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="fundraising_contribution", to="portal.familycredit")),
                ("financial_transaction", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="fundraising_contribution", to="portal.financialtransaction")),
                ("voided_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="fundraising_contributions_voided", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-received_date", "-created_at"]},
        ),
    ]
