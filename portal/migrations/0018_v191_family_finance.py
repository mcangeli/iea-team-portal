from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0017_v190_finance_foundation"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="HomeBarn",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150)),
                ("active", models.BooleanField(default=True)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("team", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="home_barns", to="portal.team")),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.AddConstraint(
            model_name="homebarn",
            constraint=models.UniqueConstraint(fields=("team", "name"), name="unique_home_barn_team_name"),
        ),
        migrations.AddField(
            model_name="seasonmembership",
            name="home_barn",
            field=models.ForeignKey(
                blank=True,
                help_text="The rider's home barn for this season. Stored on the season membership so barn changes preserve history.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="season_memberships",
                to="portal.homebarn",
            ),
        ),
        migrations.CreateModel(
            name="MembershipDuesRate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("due_date", models.DateField(blank=True, null=True)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("home_barn", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="dues_rates", to="portal.homebarn")),
                ("season", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="membership_dues_rates", to="portal.season")),
            ],
            options={"ordering": ["home_barn__name"]},
        ),
        migrations.AddConstraint(
            model_name="membershipduesrate",
            constraint=models.UniqueConstraint(fields=("season", "home_barn"), name="unique_season_home_barn_dues_rate"),
        ),
        migrations.CreateModel(
            name="FamilyCharge",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("charge_type", models.CharField(choices=[("membership_dues","Membership dues"),("show_fee","Show fee"),("lesson","Lesson / clinic"),("apparel","Apparel"),("travel","Travel"),("other","Other")], default="other", max_length=30)),
                ("description", models.CharField(max_length=180)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("charge_date", models.DateField(default=django.utils.timezone.localdate)),
                ("due_date", models.DateField(blank=True, null=True)),
                ("status", models.CharField(choices=[("open","Open"),("waived","Waived"),("closed","Closed")], default="open", max_length=20)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="family_charges_created", to=settings.AUTH_USER_MODEL)),
                ("membership", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="family_charges", to="portal.seasonmembership")),
                ("show", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="family_charges", to="portal.show")),
                ("source_dues_rate", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="generated_charges", to="portal.membershipduesrate")),
            ],
            options={"ordering": ["due_date", "charge_date", "id"]},
        ),
        migrations.CreateModel(
            name="FamilyCredit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("credit_type", models.CharField(choices=[("scholarship","Scholarship / aid"),("courtesy","Courtesy credit"),("manual","Manual adjustment"),("other","Other")], default="manual", max_length=30)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("source", models.CharField(blank=True, help_text="Who or what authorized/funded this credit.", max_length=150)),
                ("status", models.CharField(choices=[("pending","Pending"),("applied","Applied"),("cancelled","Cancelled")], default="applied", max_length=20)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("charge", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="credits", to="portal.familycharge")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="family_credits_created", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="ServiceAgreementCredit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("description", models.CharField(max_length=200)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("status", models.CharField(choices=[("pending","Pending"),("applied","Applied"),("cancelled","Cancelled")], default="pending", max_length=20)),
                ("completed_date", models.DateField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("charge", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="service_credits", to="portal.familycharge")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="service_agreements_created", to=settings.AUTH_USER_MODEL)),
                ("membership", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="service_agreements", to="portal.seasonmembership")),
                ("required_shows", models.ManyToManyField(blank=True, related_name="service_credit_agreements", to="portal.show")),
            ],
        ),
        migrations.CreateModel(
            name="FinancialAssistanceAward",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(help_text="Example: IEA", max_length=150)),
                ("program_name", models.CharField(blank=True, max_length=180)),
                ("approved_maximum", models.DecimalField(decimal_places=2, max_digits=10)),
                ("award_date", models.DateField(blank=True, null=True)),
                ("reference", models.CharField(blank=True, max_length=120)),
                ("eligible_expenses", models.TextField(blank=True, help_text="Describe the expense types covered by this award.")),
                ("status", models.CharField(choices=[("active","Active"),("exhausted","Exhausted"),("closed","Closed")], default="active", max_length=20)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assistance_awards_created", to=settings.AUTH_USER_MODEL)),
                ("membership", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="assistance_awards", to="portal.seasonmembership")),
            ],
        ),
        migrations.CreateModel(
            name="AssistanceClaim",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("family_relief_amount", models.DecimalField(decimal_places=2, help_text="Amount of this charge covered by the award and removed from the family's responsibility.", max_digits=10)),
                ("amount_requested", models.DecimalField(decimal_places=2, max_digits=10)),
                ("amount_approved", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("reimbursed_amount", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("status", models.CharField(choices=[("draft","Not submitted"),("submitted","Submitted"),("approved","Approved"),("reimbursed","Reimbursed"),("denied","Denied"),("cancelled","Cancelled")], default="draft", max_length=20)),
                ("submitted_date", models.DateField(blank=True, null=True)),
                ("approved_date", models.DateField(blank=True, null=True)),
                ("received_date", models.DateField(blank=True, null=True)),
                ("reference", models.CharField(blank=True, max_length=120)),
                ("notes", models.TextField(blank=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("award", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="claims", to="portal.financialassistanceaward")),
                ("charge", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="assistance_claims", to="portal.familycharge")),
                ("financial_transaction", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assistance_claim", to="portal.financialtransaction")),
                ("reimbursement_account", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="assistance_claims", to="portal.financialaccount")),
                ("reimbursement_category", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="assistance_claims", to="portal.financialcategory")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assistance_claims_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-submitted_date", "-id"]},
        ),
        migrations.CreateModel(
            name="FamilyPayment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("received_date", models.DateField(default=django.utils.timezone.localdate)),
                ("method", models.CharField(blank=True, max_length=80)),
                ("reference", models.CharField(blank=True, max_length=120)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="family_payments", to="portal.financialaccount")),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="family_payments", to="portal.financialcategory")),
                ("charge", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payments", to="portal.familycharge")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="family_payments_created", to=settings.AUTH_USER_MODEL)),
                ("financial_transaction", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="family_payment", to="portal.financialtransaction")),
                ("membership", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="family_payments", to="portal.seasonmembership")),
            ],
        ),
    ]
