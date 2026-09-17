from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum

from portal.models import FinancialAccount, FinancialCategory, FinancialTransaction, Season, Team


ZERO = Decimal("0.00")


class FinanceDomain(models.TextChoices):
    GENERAL = "general", "General barn"
    IEA = "iea", "IEA"


# FinancialAccount is still defined in the legacy model module. Contribute the
# v3.5 domain field here so model state stays modular without moving the legacy
# class during the compatibility-first release.
if not hasattr(FinancialAccount, "finance_domain"):
    models.CharField(
        max_length=12,
        choices=FinanceDomain.choices,
        default=FinanceDomain.GENERAL,
    ).contribute_to_class(FinancialAccount, "finance_domain")


class ReceivableAccount(models.Model):
    """Organization-scoped account receivable, separate from bank/cash accounts."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CLOSED = "closed", "Closed"

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="receivable_accounts")
    name = models.CharField(max_length=180)
    finance_domain = models.CharField(max_length=12, choices=FinanceDomain.choices, default=FinanceDomain.GENERAL)
    primary_person = models.ForeignKey(
        "portal.Person", on_delete=models.PROTECT, null=True, blank=True,
        related_name="primary_receivable_accounts",
    )
    legacy_membership = models.ForeignKey(
        "portal.SeasonMembership", on_delete=models.PROTECT, null=True, blank=True,
        related_name="receivable_accounts",
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(fields=["team", "name"], name="unique_receivable_account_team_name"),
            models.UniqueConstraint(
                fields=["legacy_membership", "finance_domain"],
                name="unique_receivable_legacy_membership_domain",
            ),
        ]

    def clean(self):
        super().clean()
        if self.primary_person_id and self.primary_person.team_id != self.team_id:
            raise ValidationError({"primary_person": "Account contact must belong to the same organization."})
        if self.legacy_membership_id and self.legacy_membership.season.team_id != self.team_id:
            raise ValidationError({"legacy_membership": "Legacy membership must belong to the same organization."})

    @property
    def balance(self):
        charges = self.charges.filter(status=ReceivableCharge.Status.POSTED).aggregate(total=Sum("amount"))["total"] or ZERO
        credits = self.credits.filter(status=ReceivableCredit.Status.POSTED).aggregate(total=Sum("amount"))["total"] or ZERO
        payments = self.payments.filter(status=ReceivablePayment.Status.POSTED).aggregate(total=Sum("amount"))["total"] or ZERO
        return charges - credits - payments

    def __str__(self):
        return self.name


class ReceivableCharge(models.Model):
    class Status(models.TextChoices):
        POSTED = "posted", "Posted"
        WAIVED = "waived", "Waived"
        VOID = "void", "Void"

    account = models.ForeignKey(ReceivableAccount, on_delete=models.PROTECT, related_name="charges")
    season = models.ForeignKey(Season, on_delete=models.PROTECT, null=True, blank=True, related_name="receivable_charges")
    legacy_family_charge = models.OneToOneField(
        "portal.FamilyCharge", on_delete=models.PROTECT, null=True, blank=True,
        related_name="receivable_charge",
    )
    description = models.CharField(max_length=220)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    charge_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    charge_type = models.CharField(max_length=40, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.POSTED)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["charge_date", "id"]
        constraints = [models.CheckConstraint(condition=models.Q(amount__gt=0), name="receivable_charge_amount_gt_zero")]

    def clean(self):
        super().clean()
        if self.season_id and self.season.team_id != self.account.team_id:
            raise ValidationError({"season": "Charge season must belong to the account organization."})
        if self.legacy_family_charge_id and self.legacy_family_charge.membership.season.team_id != self.account.team_id:
            raise ValidationError({"legacy_family_charge": "Legacy charge must belong to the account organization."})

    @property
    def allocated_total(self):
        return self.allocations.filter(status=ReceivableAllocation.Status.POSTED).aggregate(total=Sum("amount"))["total"] or ZERO

    @property
    def balance(self):
        if self.status != self.Status.POSTED:
            return ZERO
        return max(self.amount - self.allocated_total, ZERO)

    def __str__(self):
        return self.description


class ReceivableCredit(models.Model):
    class Status(models.TextChoices):
        POSTED = "posted", "Posted"
        VOID = "void", "Void"

    account = models.ForeignKey(ReceivableAccount, on_delete=models.PROTECT, related_name="credits")
    season = models.ForeignKey(Season, on_delete=models.PROTECT, null=True, blank=True, related_name="receivable_credits")
    legacy_family_credit = models.OneToOneField("portal.FamilyCredit", on_delete=models.PROTECT, null=True, blank=True, related_name="receivable_credit")
    legacy_service_credit = models.OneToOneField("portal.ServiceAgreementCredit", on_delete=models.PROTECT, null=True, blank=True, related_name="receivable_credit")
    legacy_assistance_claim = models.OneToOneField("portal.AssistanceClaim", on_delete=models.PROTECT, null=True, blank=True, related_name="receivable_credit")
    description = models.CharField(max_length=220)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    credit_date = models.DateField()
    credit_type = models.CharField(max_length=40, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.POSTED)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["credit_date", "id"]
        constraints = [models.CheckConstraint(condition=models.Q(amount__gt=0), name="receivable_credit_amount_gt_zero")]

    def clean(self):
        super().clean()
        if self.season_id and self.season.team_id != self.account.team_id:
            raise ValidationError({"season": "Credit season must belong to the account organization."})

    @property
    def allocated_total(self):
        return self.allocations.filter(status=ReceivableAllocation.Status.POSTED).aggregate(total=Sum("amount"))["total"] or ZERO

    @property
    def unapplied_amount(self):
        if self.status != self.Status.POSTED:
            return ZERO
        return max(self.amount - self.allocated_total, ZERO)


class ReceivablePayment(models.Model):
    class Status(models.TextChoices):
        POSTED = "posted", "Posted"
        VOID = "void", "Void"

    account = models.ForeignKey(ReceivableAccount, on_delete=models.PROTECT, related_name="payments")
    season = models.ForeignKey(Season, on_delete=models.PROTECT, null=True, blank=True, related_name="receivable_payments")
    legacy_family_payment = models.OneToOneField(
        "portal.FamilyPayment", on_delete=models.PROTECT, null=True, blank=True,
        related_name="receivable_payment",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    received_date = models.DateField()
    method = models.CharField(max_length=40, blank=True)
    reference = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    deposit_account = models.ForeignKey(FinancialAccount, on_delete=models.PROTECT, null=True, blank=True, related_name="receivable_payments")
    income_category = models.ForeignKey(FinancialCategory, on_delete=models.PROTECT, null=True, blank=True, related_name="receivable_payments")
    financial_transaction = models.OneToOneField(FinancialTransaction, on_delete=models.SET_NULL, null=True, blank=True, related_name="receivable_payment")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.POSTED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["received_date", "id"]
        constraints = [models.CheckConstraint(condition=models.Q(amount__gt=0), name="receivable_payment_amount_gt_zero")]

    def clean(self):
        super().clean()
        team_id = self.account.team_id
        if self.season_id and self.season.team_id != team_id:
            raise ValidationError({"season": "Payment season must belong to the account organization."})
        if self.deposit_account_id:
            if self.deposit_account.team_id != team_id:
                raise ValidationError({"deposit_account": "Deposit account must belong to the same organization."})
            if self.deposit_account.finance_domain != self.account.finance_domain:
                raise ValidationError({"deposit_account": "Deposit account must belong to the same finance domain."})
        if self.income_category_id and self.income_category.team_id != team_id:
            raise ValidationError({"income_category": "Income category must belong to the same organization."})
        if self.financial_transaction_id and self.financial_transaction.team_id != team_id:
            raise ValidationError({"financial_transaction": "Financial transaction must belong to the same organization."})

    @property
    def allocated_total(self):
        return self.allocations.filter(status=ReceivableAllocation.Status.POSTED).aggregate(total=Sum("amount"))["total"] or ZERO

    @property
    def unapplied_amount(self):
        if self.status != self.Status.POSTED:
            return ZERO
        return max(self.amount - self.allocated_total, ZERO)


class ReceivableAllocation(models.Model):
    class Status(models.TextChoices):
        POSTED = "posted", "Posted"
        VOID = "void", "Void"

    charge = models.ForeignKey(ReceivableCharge, on_delete=models.PROTECT, related_name="allocations")
    payment = models.ForeignKey(ReceivablePayment, on_delete=models.PROTECT, null=True, blank=True, related_name="allocations")
    credit = models.ForeignKey(ReceivableCredit, on_delete=models.PROTECT, null=True, blank=True, related_name="allocations")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.POSTED)
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="receivable_allocation_amount_gt_zero"),
            models.CheckConstraint(
                condition=(models.Q(payment__isnull=False, credit__isnull=True) | models.Q(payment__isnull=True, credit__isnull=False)),
                name="receivable_allocation_exactly_one_source",
            ),
        ]

    @property
    def source(self):
        return self.payment or self.credit

    def clean(self):
        super().clean()
        if bool(self.payment_id) == bool(self.credit_id):
            raise ValidationError("An allocation must have exactly one payment or credit source.")
        source = self.source
        if source and source.account_id != self.charge.account_id:
            raise ValidationError("Allocation source and charge must belong to the same receivable account.")
        if source and source.account.finance_domain != self.charge.account.finance_domain:
            raise ValidationError("Allocation source and charge must belong to the same finance domain.")
        if self.status == self.Status.POSTED and source:
            if source.status != source.Status.POSTED:
                raise ValidationError("A void source cannot be allocated.")
            existing = source.allocations.filter(status=self.Status.POSTED).exclude(pk=self.pk).aggregate(total=Sum("amount"))["total"] or ZERO
            if existing + self.amount > source.amount:
                raise ValidationError({"amount": "Allocation exceeds the source amount."})
            charge_existing = self.charge.allocations.filter(status=self.Status.POSTED).exclude(pk=self.pk).aggregate(total=Sum("amount"))["total"] or ZERO
            if charge_existing + self.amount > self.charge.amount:
                raise ValidationError({"amount": "Allocation exceeds the charge amount."})

    def __str__(self):
        return f"{self.amount} → {self.charge}"
