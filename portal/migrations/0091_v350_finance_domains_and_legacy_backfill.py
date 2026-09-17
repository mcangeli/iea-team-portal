import django.db.models.deletion
from django.db import migrations, models


def backfill_legacy_iea_receivables(apps, schema_editor):
    FinancialAccount = apps.get_model("portal", "FinancialAccount")
    FamilyCharge = apps.get_model("portal", "FamilyCharge")
    FamilyCredit = apps.get_model("portal", "FamilyCredit")
    ServiceAgreementCredit = apps.get_model("portal", "ServiceAgreementCredit")
    AssistanceClaim = apps.get_model("portal", "AssistanceClaim")
    FamilyPayment = apps.get_model("portal", "FamilyPayment")
    ReceivableAccount = apps.get_model("portal", "ReceivableAccount")
    ReceivableCharge = apps.get_model("portal", "ReceivableCharge")
    ReceivableCredit = apps.get_model("portal", "ReceivableCredit")
    ReceivablePayment = apps.get_model("portal", "ReceivablePayment")
    ReceivableAllocation = apps.get_model("portal", "ReceivableAllocation")

    FinancialAccount.objects.all().update(finance_domain="iea")

    account_by_membership = {}
    charge_by_legacy_id = {}

    for legacy in FamilyCharge.objects.select_related("membership__rider", "membership__season").order_by("id"):
        membership = legacy.membership
        account = account_by_membership.get(membership.id)
        if account is None:
            account, _ = ReceivableAccount.objects.get_or_create(
                legacy_membership_id=membership.id,
                finance_domain="iea",
                defaults={
                    "team_id": membership.season.team_id,
                    "name": f"{membership.rider} — {membership.season.name} — IEA #{membership.id}",
                },
            )
            account_by_membership[membership.id] = account

        status = "waived" if legacy.status == "waived" else "posted"
        charge = ReceivableCharge.objects.create(
            account_id=account.id,
            season_id=membership.season_id,
            description=legacy.description,
            amount=legacy.amount,
            charge_date=legacy.charge_date,
            due_date=legacy.due_date,
            charge_type=legacy.charge_type,
            status=status,
            notes=legacy.notes,
            legacy_family_charge_id=legacy.id,
        )
        charge_by_legacy_id[legacy.id] = charge

    def account_for_membership(membership):
        account = account_by_membership.get(membership.id)
        if account is None:
            account, _ = ReceivableAccount.objects.get_or_create(
                legacy_membership_id=membership.id,
                finance_domain="iea",
                defaults={
                    "team_id": membership.season.team_id,
                    "name": f"{membership.rider} — {membership.season.name} — IEA #{membership.id}",
                },
            )
            account_by_membership[membership.id] = account
        return account

    for legacy in FamilyCredit.objects.select_related("charge__membership__season").order_by("id"):
        if legacy.status != "applied":
            continue
        charge = charge_by_legacy_id.get(legacy.charge_id)
        if not charge:
            continue
        credit = ReceivableCredit.objects.create(
            account_id=charge.account_id,
            season_id=legacy.charge.membership.season_id,
            description=legacy.source or legacy.get_credit_type_display(),
            amount=legacy.amount,
            credit_date=legacy.created_at.date(),
            credit_type=f"legacy_family_credit:{legacy.credit_type}",
            status="posted",
            notes=legacy.notes,
            legacy_family_credit_id=legacy.id,
        )
        ReceivableAllocation.objects.create(charge_id=charge.id, credit_id=credit.id, amount=legacy.amount)

    for legacy in ServiceAgreementCredit.objects.select_related("charge__membership__season").order_by("id"):
        if legacy.status != "applied":
            continue
        charge = charge_by_legacy_id.get(legacy.charge_id)
        if not charge:
            continue
        credit = ReceivableCredit.objects.create(
            account_id=charge.account_id,
            season_id=legacy.charge.membership.season_id,
            description=legacy.description,
            amount=legacy.amount,
            credit_date=legacy.completed_date or legacy.updated_at.date(),
            credit_type="legacy_service_agreement",
            status="posted",
            notes=legacy.notes,
            legacy_service_credit_id=legacy.id,
        )
        ReceivableAllocation.objects.create(charge_id=charge.id, credit_id=credit.id, amount=legacy.amount)

    eligible_claim_statuses = {"submitted", "approved", "reimbursed"}
    for legacy in AssistanceClaim.objects.select_related("charge__membership__season", "award").order_by("id"):
        if legacy.status not in eligible_claim_statuses or legacy.family_relief_amount <= 0:
            continue
        charge = charge_by_legacy_id.get(legacy.charge_id)
        if not charge:
            continue
        credit = ReceivableCredit.objects.create(
            account_id=charge.account_id,
            season_id=legacy.charge.membership.season_id,
            description=legacy.award.program_name or legacy.award.provider,
            amount=legacy.family_relief_amount,
            credit_date=legacy.approved_date or legacy.submitted_date or legacy.updated_at.date(),
            credit_type="legacy_assistance",
            status="posted",
            notes=legacy.notes,
            legacy_assistance_claim_id=legacy.id,
        )
        ReceivableAllocation.objects.create(charge_id=charge.id, credit_id=credit.id, amount=legacy.family_relief_amount)

    for legacy in FamilyPayment.objects.select_related("membership__season", "charge").order_by("id"):
        account = account_for_membership(legacy.membership)
        payment = ReceivablePayment.objects.create(
            account_id=account.id,
            season_id=legacy.membership.season_id,
            amount=legacy.amount,
            received_date=legacy.received_date,
            method=legacy.method,
            reference=legacy.reference,
            notes=legacy.notes,
            deposit_account_id=legacy.account_id,
            income_category_id=legacy.category_id,
            financial_transaction_id=legacy.financial_transaction_id,
            status="posted" if legacy.status == "posted" else "void",
            legacy_family_payment_id=legacy.id,
        )
        charge = charge_by_legacy_id.get(legacy.charge_id)
        if legacy.status == "posted" and charge:
            ReceivableAllocation.objects.create(charge_id=charge.id, payment_id=payment.id, amount=legacy.amount)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    # PostgreSQL cannot create the deferred indexes for the newly-added foreign
    # keys while RunPython has pending trigger events in the same transaction.
    # Running this compatibility migration non-atomically lets each schema
    # operation finish before the data backfill begins.
    atomic = False

    dependencies = [("portal", "0090_v350_receivables_foundation")]

    operations = [
        migrations.AddField(
            model_name="financialaccount",
            name="finance_domain",
            field=models.CharField(choices=[("general", "General barn"), ("iea", "IEA")], default="general", max_length=12),
        ),
        migrations.AddField(
            model_name="receivableaccount",
            name="finance_domain",
            field=models.CharField(choices=[("general", "General barn"), ("iea", "IEA")], default="general", max_length=12),
        ),
        migrations.AddField(
            model_name="receivableaccount",
            name="legacy_membership",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="receivable_accounts", to="portal.seasonmembership"),
        ),
        migrations.AddField(
            model_name="receivablecharge",
            name="legacy_family_charge",
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="receivable_charge", to="portal.familycharge"),
        ),
        migrations.AddField(
            model_name="receivablecredit",
            name="legacy_family_credit",
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="receivable_credit", to="portal.familycredit"),
        ),
        migrations.AddField(
            model_name="receivablecredit",
            name="legacy_service_credit",
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="receivable_credit", to="portal.serviceagreementcredit"),
        ),
        migrations.AddField(
            model_name="receivablecredit",
            name="legacy_assistance_claim",
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="receivable_credit", to="portal.assistanceclaim"),
        ),
        migrations.AddField(
            model_name="receivablepayment",
            name="legacy_family_payment",
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="receivable_payment", to="portal.familypayment"),
        ),
        migrations.AddConstraint(
            model_name="receivableaccount",
            constraint=models.UniqueConstraint(fields=("legacy_membership", "finance_domain"), name="unique_receivable_legacy_membership_domain"),
        ),
        migrations.RunPython(backfill_legacy_iea_receivables, noop_reverse),
    ]
