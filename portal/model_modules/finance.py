from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from portal.models import FinancialAccount, FinancialCategory, FinancialTransaction, Season, Team
ZERO = Decimal("0.00")
class FinanceDomain(models.TextChoices):
    GENERAL="general","General barn"
    IEA="iea","IEA"
if not hasattr(FinancialAccount,"finance_domain"): models.CharField(max_length=12,choices=FinanceDomain.choices,default=FinanceDomain.GENERAL).contribute_to_class(FinancialAccount,"finance_domain")
class ReceivableAccount(models.Model):
    class Status(models.TextChoices): ACTIVE="active","Active"; CLOSED="closed","Closed"
    team=models.ForeignKey(Team,on_delete=models.CASCADE,related_name="receivable_accounts"); name=models.CharField(max_length=180); finance_domain=models.CharField(max_length=12,choices=FinanceDomain.choices,default=FinanceDomain.GENERAL); primary_person=models.ForeignKey("portal.Person",on_delete=models.PROTECT,null=True,blank=True,related_name="primary_receivable_accounts"); legacy_membership=models.ForeignKey("portal.SeasonMembership",on_delete=models.PROTECT,null=True,blank=True,related_name="receivable_accounts"); status=models.CharField(max_length=12,choices=Status.choices,default=Status.ACTIVE); notes=models.TextField(blank=True); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta:
        ordering=["name","id"]; constraints=[models.UniqueConstraint(fields=["team","finance_domain","name"],name="unique_receivable_account_team_domain_name"),models.UniqueConstraint(fields=["legacy_membership","finance_domain"],name="unique_receivable_legacy_membership_domain")]
    def clean(self):
        super().clean()
        if self.primary_person_id and self.primary_person.team_id!=self.team_id: raise ValidationError({"primary_person":"Account contact must belong to the same organization."})
        if self.legacy_membership_id and self.legacy_membership.season.team_id!=self.team_id: raise ValidationError({"legacy_membership":"Legacy membership must belong to the same organization."})
    @property
    def amount_due(self): return sum((charge.balance for charge in self.charges.all()),ZERO)
    @property
    def unapplied_payment_total(self): return sum((payment.unapplied_amount for payment in self.payments.all()),ZERO)
    @property
    def unapplied_credit_total(self): return sum((credit.unapplied_amount for credit in self.credits.all()),ZERO)
    @property
    def balance(self): return self.amount_due-self.unapplied_payment_total-self.unapplied_credit_total
    def __str__(self): return self.name
class ReceivableAccountPerson(models.Model):
    class Role(models.TextChoices):
        RESPONSIBLE_PARTY="responsible_party","Responsible party"; BILLING_CONTACT="billing_contact","Billing contact"; PARTICIPANT="participant","Rider / participant"
    account=models.ForeignKey(ReceivableAccount,on_delete=models.CASCADE,related_name="people_links"); person=models.ForeignKey("portal.Person",on_delete=models.PROTECT,related_name="receivable_account_links"); role=models.CharField(max_length=24,choices=Role.choices,default=Role.PARTICIPANT); statement_recipient=models.BooleanField(default=False); active=models.BooleanField(default=True); notes=models.CharField(max_length=255,blank=True); created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=["account_id","role","person_id"]; constraints=[models.UniqueConstraint(fields=["account","person","role"],name="unique_receivable_account_person_role")]
    def clean(self):
        super().clean()
        if self.person_id and self.account_id and self.person.team_id!=self.account.team_id: raise ValidationError({"person":"Account person must belong to the same organization."})
    def __str__(self): return f"{self.account}: {self.person} ({self.get_role_display()})"

class ReceivableCharge(models.Model):
    class Status(models.TextChoices): POSTED="posted","Posted"; WAIVED="waived","Waived"; VOID="void","Void"
    account=models.ForeignKey(ReceivableAccount,on_delete=models.PROTECT,related_name="charges"); season=models.ForeignKey(Season,on_delete=models.PROTECT,null=True,blank=True,related_name="receivable_charges"); legacy_family_charge=models.OneToOneField("portal.FamilyCharge",on_delete=models.PROTECT,null=True,blank=True,related_name="receivable_charge"); description=models.CharField(max_length=220); amount=models.DecimalField(max_digits=12,decimal_places=2); charge_date=models.DateField(); due_date=models.DateField(null=True,blank=True); charge_type=models.CharField(max_length=40,blank=True); status=models.CharField(max_length=12,choices=Status.choices,default=Status.POSTED); notes=models.TextField(blank=True); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta: ordering=["charge_date","id"]; constraints=[models.CheckConstraint(condition=models.Q(amount__gt=0),name="receivable_charge_amount_gt_zero")]
    def clean(self):
        super().clean()
        if self.season_id and self.season.team_id!=self.account.team_id: raise ValidationError({"season":"Charge season must belong to the account organization."})
        if self.legacy_family_charge_id and self.legacy_family_charge.membership.season.team_id!=self.account.team_id: raise ValidationError({"legacy_family_charge":"Legacy charge must belong to the account organization."})
    @property
    def allocated_total(self): return self.allocations.filter(status=ReceivableAllocation.Status.POSTED).aggregate(total=Sum("amount"))["total"] or ZERO
    @property
    def balance(self): return ZERO if self.status!=self.Status.POSTED else max(self.amount-self.allocated_total,ZERO)
    def __str__(self): return self.description

class ReceivableCredit(models.Model):
    class Status(models.TextChoices): POSTED="posted","Posted"; VOID="void","Void"
    account=models.ForeignKey(ReceivableAccount,on_delete=models.PROTECT,related_name="credits"); season=models.ForeignKey(Season,on_delete=models.PROTECT,null=True,blank=True,related_name="receivable_credits"); legacy_family_credit=models.OneToOneField("portal.FamilyCredit",on_delete=models.PROTECT,null=True,blank=True,related_name="receivable_credit"); legacy_service_credit=models.OneToOneField("portal.ServiceAgreementCredit",on_delete=models.PROTECT,null=True,blank=True,related_name="receivable_credit"); legacy_assistance_claim=models.OneToOneField("portal.AssistanceClaim",on_delete=models.PROTECT,null=True,blank=True,related_name="receivable_credit"); description=models.CharField(max_length=220); amount=models.DecimalField(max_digits=12,decimal_places=2); credit_date=models.DateField(); credit_type=models.CharField(max_length=40,blank=True); status=models.CharField(max_length=12,choices=Status.choices,default=Status.POSTED); notes=models.TextField(blank=True); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta: ordering=["credit_date","id"]; constraints=[models.CheckConstraint(condition=models.Q(amount__gt=0),name="receivable_credit_amount_gt_zero")]
    def clean(self):
        super().clean()
        if self.season_id and self.season.team_id!=self.account.team_id: raise ValidationError({"season":"Credit season must belong to the account organization."})
    @property
    def allocated_total(self): return self.allocations.filter(status=ReceivableAllocation.Status.POSTED).aggregate(total=Sum("amount"))["total"] or ZERO
    @property
    def unapplied_amount(self): return ZERO if self.status!=self.Status.POSTED else max(self.amount-self.allocated_total,ZERO)
    def __str__(self): return self.description

class ReceivablePayment(models.Model):
    class Status(models.TextChoices): POSTED="posted","Posted"; VOID="void","Void"
    account=models.ForeignKey(ReceivableAccount,on_delete=models.PROTECT,related_name="payments"); season=models.ForeignKey(Season,on_delete=models.PROTECT,null=True,blank=True,related_name="receivable_payments"); legacy_family_payment=models.OneToOneField("portal.FamilyPayment",on_delete=models.PROTECT,null=True,blank=True,related_name="receivable_payment"); amount=models.DecimalField(max_digits=12,decimal_places=2); received_date=models.DateField(); method=models.CharField(max_length=40,blank=True); reference=models.CharField(max_length=120,blank=True); notes=models.TextField(blank=True); deposit_account=models.ForeignKey(FinancialAccount,on_delete=models.PROTECT,null=True,blank=True,related_name="receivable_payments"); income_category=models.ForeignKey(FinancialCategory,on_delete=models.PROTECT,null=True,blank=True,related_name="receivable_payments"); financial_transaction=models.OneToOneField(FinancialTransaction,on_delete=models.PROTECT,null=True,blank=True,related_name="receivable_payment"); status=models.CharField(max_length=12,choices=Status.choices,default=Status.POSTED); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta: ordering=["received_date","id"]; constraints=[models.CheckConstraint(condition=models.Q(amount__gt=0),name="receivable_payment_amount_gt_zero")]
    def clean(self):
        super().clean()
        if self.season_id and self.season.team_id!=self.account.team_id: raise ValidationError({"season":"Payment season must belong to the account organization."})
        if self.deposit_account_id and (self.deposit_account.team_id!=self.account.team_id or self.deposit_account.finance_domain!=self.account.finance_domain): raise ValidationError({"deposit_account":"Deposit account must belong to the same organization and finance domain."})
        if self.income_category_id and self.income_category.team_id!=self.account.team_id: raise ValidationError({"income_category":"Income category must belong to the same organization."})
        if self.financial_transaction_id and self.financial_transaction.team_id!=self.account.team_id: raise ValidationError({"financial_transaction":"Financial transaction must belong to the same organization."})
    @property
    def allocated_total(self): return self.allocations.filter(status=ReceivableAllocation.Status.POSTED).aggregate(total=Sum("amount"))["total"] or ZERO
    @property
    def unapplied_amount(self): return ZERO if self.status!=self.Status.POSTED else max(self.amount-self.allocated_total,ZERO)
    def __str__(self): return f"{self.received_date}: {self.amount}"

class ReceivableAllocation(models.Model):
    class Status(models.TextChoices): POSTED="posted","Posted"; VOID="void","Void"
    charge=models.ForeignKey(ReceivableCharge,on_delete=models.PROTECT,related_name="allocations"); payment=models.ForeignKey(ReceivablePayment,on_delete=models.PROTECT,null=True,blank=True,related_name="allocations"); credit=models.ForeignKey(ReceivableCredit,on_delete=models.PROTECT,null=True,blank=True,related_name="allocations"); amount=models.DecimalField(max_digits=12,decimal_places=2); status=models.CharField(max_length=12,choices=Status.choices,default=Status.POSTED); notes=models.CharField(max_length=255,blank=True); created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=["created_at","id"]; constraints=[models.CheckConstraint(condition=models.Q(amount__gt=0),name="receivable_allocation_amount_gt_zero"),models.CheckConstraint(condition=(models.Q(payment__isnull=False,credit__isnull=True)|models.Q(payment__isnull=True,credit__isnull=False)),name="receivable_allocation_exactly_one_source")]
    def clean(self):
        super().clean(); source=self.payment or self.credit
        if bool(self.payment_id)==bool(self.credit_id): raise ValidationError("Allocation must use exactly one payment or credit.")
        if source and source.account_id!=self.charge.account_id: raise ValidationError("Allocation source and charge must belong to the same receivable account.")
        if source and source.account.finance_domain!=self.charge.account.finance_domain: raise ValidationError("Allocation source and charge must belong to the same finance domain.")
        if source and source.status!=source.Status.POSTED: raise ValidationError("Only posted payments or credits may be allocated.")
        if self.amount and source and self.amount>source.unapplied_amount+(self.amount if self.pk else ZERO): raise ValidationError("Allocation exceeds the source's unapplied amount.")
        if self.amount and self.amount>self.charge.balance+(self.amount if self.pk else ZERO): raise ValidationError("Allocation exceeds the charge balance.")
    def __str__(self): return f"{self.charge}: {self.amount}"


class BankImportProfile(models.Model):
    team=models.ForeignKey(Team,on_delete=models.CASCADE,related_name="bank_import_profiles"); financial_account=models.ForeignKey(FinancialAccount,on_delete=models.PROTECT,related_name="import_profiles"); name=models.CharField(max_length=120); file_type=models.CharField(max_length=8,choices=[("csv","CSV"),("xlsx","Excel")],default="csv"); column_mapping=models.JSONField(default=dict); active=models.BooleanField(default=True); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=["name","id"]; constraints=[models.UniqueConstraint(fields=["team","financial_account","name"],name="unique_bank_import_profile_account_name")]
    def clean(self):
        super().clean()
        if self.financial_account_id and self.financial_account.team_id!=self.team_id:raise ValidationError({"financial_account":"Import profile account must belong to the same organization."})

class BankImportBatch(models.Model):
    class Status(models.TextChoices): STAGED="staged","Staged"; REVIEWED="reviewed","Reviewed"; COMPLETED="completed","Completed"; VOID="void","Void"
    team=models.ForeignKey(Team,on_delete=models.CASCADE,related_name="bank_import_batches"); financial_account=models.ForeignKey(FinancialAccount,on_delete=models.PROTECT,related_name="import_batches"); profile=models.ForeignKey(BankImportProfile,on_delete=models.PROTECT,null=True,blank=True,related_name="batches"); finance_domain=models.CharField(max_length=12,choices=FinanceDomain.choices); source_name=models.CharField(max_length=255); source_fingerprint=models.CharField(max_length=64); status=models.CharField(max_length=12,choices=Status.choices,default=Status.STAGED); imported_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=["-imported_at","-id"]; constraints=[models.UniqueConstraint(fields=["team","financial_account","source_fingerprint"],name="unique_bank_import_batch_fingerprint")]
    def clean(self):
        super().clean()
        if self.financial_account_id and (self.financial_account.team_id!=self.team_id or self.financial_account.finance_domain!=self.finance_domain):raise ValidationError({"financial_account":"Import batch account must match the organization and finance domain."})
        if self.profile_id and self.profile.financial_account_id!=self.financial_account_id:raise ValidationError({"profile":"Import profile must belong to the selected financial account."})

class ImportedBankTransaction(models.Model):
    class Direction(models.TextChoices): CREDIT="credit","Money in"; DEBIT="debit","Money out"
    class Status(models.TextChoices): STAGED="staged","Staged"; MATCHED="matched","Matched"; RECONCILED="reconciled","Reconciled"; IGNORED="ignored","Ignored"
    batch=models.ForeignKey(BankImportBatch,on_delete=models.CASCADE,related_name="transactions"); transaction_date=models.DateField(); posted_date=models.DateField(null=True,blank=True); amount=models.DecimalField(max_digits=12,decimal_places=2); direction=models.CharField(max_length=8,choices=Direction.choices); description=models.CharField(max_length=255); reference=models.CharField(max_length=160,blank=True); external_id=models.CharField(max_length=160,blank=True); row_fingerprint=models.CharField(max_length=64); raw_data=models.JSONField(default=dict); status=models.CharField(max_length=12,choices=Status.choices,default=Status.STAGED); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=["transaction_date","id"]; constraints=[models.CheckConstraint(condition=models.Q(amount__gt=0),name="imported_bank_transaction_amount_gt_zero"),models.UniqueConstraint(fields=["batch","row_fingerprint"],name="unique_imported_bank_transaction_batch_row")]

class ReconciliationMatch(models.Model):
    class Status(models.TextChoices): SUGGESTED="suggested","Suggested"; CONFIRMED="confirmed","Confirmed"; REJECTED="rejected","Rejected"
    imported_transaction=models.ForeignKey(ImportedBankTransaction,on_delete=models.PROTECT,related_name="matches"); financial_transaction=models.ForeignKey(FinancialTransaction,on_delete=models.PROTECT,related_name="bank_matches"); status=models.CharField(max_length=12,choices=Status.choices,default=Status.SUGGESTED); score=models.PositiveSmallIntegerField(default=0); rationale=models.CharField(max_length=255,blank=True); confirmed_at=models.DateTimeField(null=True,blank=True); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=["-score","id"]; constraints=[models.UniqueConstraint(fields=["imported_transaction","financial_transaction"],name="unique_reconciliation_candidate")]
    def clean(self):
        super().clean()
        imported_account=self.imported_transaction.batch.financial_account if self.imported_transaction_id else None
        if imported_account and self.financial_transaction_id and (self.financial_transaction.team_id!=self.imported_transaction.batch.team_id or self.financial_transaction.account_id!=imported_account.id):raise ValidationError("Reconciliation matches must stay within the imported financial account.")
