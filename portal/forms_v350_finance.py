from django import forms
from django.core.exceptions import ValidationError
from portal.model_modules.finance import AccountingExportProfile, BankImportProfile, Budget, BudgetLine, FinanceDomain, PayableParty, ReceivableAccount, ReceivableAccountPerson, ReceivableBillingRule, ReceivableCreditRule
from portal.model_modules.people import Person
from portal.models import FinancialAccount, FinancialCategory, Season


class PayablePartyForm(forms.Form):
    name=forms.CharField(max_length=160,label="Payee / vendor name")
    finance_domain=forms.ChoiceField(choices=FinanceDomain.choices,label="Finance area")
    party_type=forms.ChoiceField(choices=PayableParty.PartyType.choices,label="Type")
    contact_person=forms.ModelChoiceField(queryset=Person.objects.none(),required=False,empty_label="No linked person")
    email=forms.EmailField(required=False)
    phone=forms.CharField(max_length=40,required=False)
    notes=forms.CharField(required=False,widget=forms.Textarea(attrs={"rows":3}))
    def __init__(self,*args,team=None,allowed_domains=None,**kwargs):
        super().__init__(*args,**kwargs)
        allowed=set(allowed_domains or [])
        self.fields["finance_domain"].choices=[(v,l) for v,l in FinanceDomain.choices if v in allowed]
        self.fields["contact_person"].queryset=Person.objects.filter(team=team,active=True).order_by("last_name","first_name") if team else Person.objects.none()

class PayableObligationForm(forms.Form):
    expense_category=forms.ModelChoiceField(queryset=FinancialCategory.objects.none(),label="Expense category")
    description=forms.CharField(max_length=220)
    amount=forms.DecimalField(max_digits=12,decimal_places=2,min_value=0.01)
    obligation_date=forms.DateField(widget=forms.DateInput(attrs={"type":"date"}),label="Bill date")
    due_date=forms.DateField(required=False,widget=forms.DateInput(attrs={"type":"date"}))
    season=forms.ModelChoiceField(queryset=Season.objects.none(),required=False,empty_label="No season")
    reference=forms.CharField(max_length=120,required=False,label="Invoice / reference")
    notes=forms.CharField(required=False,widget=forms.Textarea(attrs={"rows":3}))
    def __init__(self,*args,team=None,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields["expense_category"].queryset=FinancialCategory.objects.filter(team=team,active=True,kind__in=[FinancialCategory.Kind.EXPENSE,FinancialCategory.Kind.BOTH]).order_by("sort_order","name") if team else FinancialCategory.objects.none()
        self.fields["season"].queryset=Season.objects.filter(team=team).order_by("-start_date") if team else Season.objects.none()

class PayablePaymentForm(forms.Form):
    amount=forms.DecimalField(max_digits=12,decimal_places=2,min_value=0.01)
    paid_date=forms.DateField(widget=forms.DateInput(attrs={"type":"date"}),label="Payment date")
    payment_account=forms.ModelChoiceField(queryset=FinancialAccount.objects.none(),label="Pay from")
    method=forms.CharField(max_length=40,required=False)
    reference=forms.CharField(max_length=120,required=False)
    notes=forms.CharField(required=False,widget=forms.Textarea(attrs={"rows":3}))
    def __init__(self,*args,team=None,finance_domain=None,max_amount=None,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields["payment_account"].queryset=FinancialAccount.objects.filter(team=team,finance_domain=finance_domain,active=True).order_by("name") if team else FinancialAccount.objects.none()
        if max_amount is not None:
            self.fields["amount"].max_value=max_amount
            self.fields["amount"].widget.attrs["max"]=max_amount

class PayableVoidPaymentForm(forms.Form):
    reason=forms.CharField(max_length=255,widget=forms.Textarea(attrs={"rows":3}),help_text="Required audit reason for voiding this payment.")


class ReceivableBillingRuleForm(forms.Form):
    account=forms.ModelChoiceField(queryset=ReceivableAccount.objects.none(),label="Receivable account")
    description=forms.CharField(max_length=220)
    amount=forms.DecimalField(max_digits=12,decimal_places=2,min_value=0.01)
    cadence=forms.ChoiceField(choices=ReceivableBillingRule.Cadence.choices)
    charge_type=forms.CharField(max_length=40,required=False,help_text="Examples: board, training, lesson, lease, care")
    due_days=forms.IntegerField(min_value=0,max_value=365,initial=0,label="Due days after charge")
    notes=forms.CharField(required=False,widget=forms.Textarea(attrs={"rows":3}))
    def __init__(self,*args,accounts=None,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields["account"].queryset=accounts if accounts is not None else ReceivableAccount.objects.none()

class ReceivableCreditRuleForm(forms.ModelForm):
    class Meta:
        model=ReceivableCreditRule
        fields=["name","source_type","calculation","rate","credit_type","active","notes"]
        labels={"source_type":"Activity source","rate":"Credit amount / rate","credit_type":"Credit category"}
        help_texts={
            "source_type":"Examples: barn_work, lesson_horse_use, show_horse_use",
            "credit_type":"Examples: work, horse_use, board_credit",
        }
        widgets={"notes":forms.Textarea(attrs={"rows":3})}
    def __init__(self,*args,team=None,finance_domain=None,**kwargs):
        super().__init__(*args,**kwargs)
        self.team=team;self.finance_domain=finance_domain
        if self.instance and not self.instance.pk:
            self.instance.team=team;self.instance.finance_domain=finance_domain
    def clean_source_type(self):
        return (self.cleaned_data["source_type"] or "").strip().lower()

class MonthlyBillingRunForm(forms.Form):
    billing_month=forms.DateField(widget=forms.DateInput(attrs={"type":"month"}),input_formats=["%Y-%m","%Y-%m-%d"],label="Billing month")


class FinanceAccountForm(forms.Form):
    name=forms.CharField(max_length=160); finance_domain=forms.ChoiceField(choices=FinanceDomain.choices); primary_person=forms.ModelChoiceField(queryset=Person.objects.none(),required=False,empty_label="No primary person"); notes=forms.CharField(required=False,widget=forms.Textarea(attrs={"rows":3}))
    def __init__(self,*args,team=None,allowed_domains=None,**kwargs):
        super().__init__(*args,**kwargs); self.fields["primary_person"].queryset=Person.objects.filter(team=team,active=True).order_by("last_name","first_name") if team else Person.objects.none(); allowed=set(allowed_domains or []); self.fields["finance_domain"].choices=[(v,l) for v,l in FinanceDomain.choices if v in allowed]

class FinanceAccountPersonForm(forms.Form):
    person=forms.ModelChoiceField(queryset=Person.objects.none()); role=forms.ChoiceField(choices=ReceivableAccountPerson.Role.choices); statement_recipient=forms.BooleanField(required=False); notes=forms.CharField(required=False,max_length=255)
    def __init__(self,*args,team=None,**kwargs):
        super().__init__(*args,**kwargs); self.fields["person"].queryset=Person.objects.filter(team=team,active=True).order_by("last_name","first_name") if team else Person.objects.none()

class FinanceChargeForm(forms.Form):
    description=forms.CharField(max_length=220); amount=forms.DecimalField(max_digits=12,decimal_places=2,min_value=0.01); charge_date=forms.DateField(widget=forms.DateInput(attrs={"type":"date"})); due_date=forms.DateField(required=False,widget=forms.DateInput(attrs={"type":"date"})); charge_type=forms.CharField(max_length=40,required=False); notes=forms.CharField(required=False,widget=forms.Textarea(attrs={"rows":3}))
class FinancePaymentForm(forms.Form):
    amount=forms.DecimalField(max_digits=12,decimal_places=2,min_value=0.01); received_date=forms.DateField(widget=forms.DateInput(attrs={"type":"date"})); deposit_account=forms.ModelChoiceField(queryset=FinancialAccount.objects.none(),label="Deposit to"); income_category=forms.ModelChoiceField(queryset=FinancialCategory.objects.none(),label="Income category"); method=forms.CharField(max_length=40,required=False); reference=forms.CharField(max_length=120,required=False); charge_id=forms.IntegerField(required=False,widget=forms.HiddenInput()); notes=forms.CharField(required=False,widget=forms.Textarea(attrs={"rows":3}))
    def __init__(self,*args,team=None,finance_domain=None,**kwargs):
        super().__init__(*args,**kwargs)
        if team:
            self.fields["deposit_account"].queryset=FinancialAccount.objects.filter(team=team,finance_domain=finance_domain,active=True).order_by("name")
            self.fields["income_category"].queryset=FinancialCategory.objects.filter(team=team,active=True,kind__in=[FinancialCategory.Kind.INCOME,FinancialCategory.Kind.BOTH]).order_by("sort_order","name")
class FinanceCreditForm(forms.Form):
    description=forms.CharField(max_length=220); amount=forms.DecimalField(max_digits=12,decimal_places=2,min_value=0.01); credit_date=forms.DateField(widget=forms.DateInput(attrs={"type":"date"})); credit_type=forms.CharField(max_length=40,required=False); charge_id=forms.IntegerField(required=False,widget=forms.HiddenInput()); notes=forms.CharField(required=False,widget=forms.Textarea(attrs={"rows":3}))
class FinanceAllocationForm(forms.Form):
    charge_id=forms.IntegerField(); amount=forms.DecimalField(max_digits=12,decimal_places=2,min_value=0.01,required=False); notes=forms.CharField(max_length=255,required=False)

class FinanceVoidPaymentForm(forms.Form):
    reason=forms.CharField(max_length=255,widget=forms.Textarea(attrs={"rows":3}),help_text="Required audit reason for voiding this payment.")

class FinanceUnallocateForm(forms.Form):
    reason=forms.CharField(max_length=255,required=False,widget=forms.Textarea(attrs={"rows":3}),help_text="Optional note explaining the allocation correction.")


class BankImportUploadForm(forms.Form):
    financial_account=forms.ModelChoiceField(queryset=FinancialAccount.objects.none(),label="Bank account")
    statement=forms.FileField(help_text="Upload a CSV or XLSX statement.")
    profile=forms.ModelChoiceField(queryset=BankImportProfile.objects.none(),required=False,empty_label="Use manual mapping",label="Saved import profile")
    def __init__(self,*args,team=None,allowed_domains=None,**kwargs):
        super().__init__(*args,**kwargs);domains=list(allowed_domains or [])
        self.fields["financial_account"].queryset=FinancialAccount.objects.filter(team=team,finance_domain__in=domains,active=True).order_by("finance_domain","name") if team else FinancialAccount.objects.none()
        self.fields["profile"].queryset=BankImportProfile.objects.filter(team=team,financial_account__finance_domain__in=domains,active=True).select_related("financial_account").order_by("financial_account__name","name") if team else BankImportProfile.objects.none()
    def clean_statement(self):
        uploaded=self.cleaned_data["statement"];name=uploaded.name.lower()
        if not (name.endswith(".csv") or name.endswith(".xlsx")):raise forms.ValidationError("Upload a CSV or XLSX bank statement.")
        return uploaded

class BankImportMappingForm(forms.Form):
    date=forms.CharField(max_length=120,label="Transaction date column")
    posted_date=forms.CharField(max_length=120,required=False,label="Posted date column")
    description=forms.CharField(max_length=120,label="Description column")
    amount=forms.CharField(max_length=120,required=False,label="Signed amount column")
    credit=forms.CharField(max_length=120,required=False,label="Credit column")
    debit=forms.CharField(max_length=120,required=False,label="Debit column")
    reference=forms.CharField(max_length=120,required=False,label="Reference column")
    external_id=forms.CharField(max_length=120,required=False,label="External ID column")
    profile_name=forms.CharField(max_length=160,required=False,label="Save mapping as")
    def clean(self):
        cleaned=super().clean()
        if not cleaned.get("amount") and not (cleaned.get("credit") and cleaned.get("debit")):raise forms.ValidationError("Map either a signed amount column or both credit and debit columns.")
        return cleaned


class AccountingExportProfileForm(forms.ModelForm):
    PRESET_QUICKBOOKS="quickbooks"
    PRESET_CUSTOM="custom"
    preset=forms.ChoiceField(choices=[(PRESET_QUICKBOOKS,"QuickBooks-friendly"),(PRESET_CUSTOM,"Custom mapping")],initial=PRESET_QUICKBOOKS)
    column_mapping=forms.JSONField(required=False,widget=forms.Textarea(attrs={"rows":8}),help_text='JSON object mapping export column names to ArenaLine fields.')
    class Meta:
        model=AccountingExportProfile
        fields=["name","finance_domain","file_type","active","column_mapping"]
    def __init__(self,*args,allowed_domains=None,**kwargs):
        super().__init__(*args,**kwargs)
        allowed=set(allowed_domains or [])
        self.fields["finance_domain"].choices=[(v,l) for v,l in FinanceDomain.choices if v in allowed]
        if self.instance and self.instance.pk:
            from portal.services.finance_exports import QUICKBOOKS_MAPPING
            self.fields["preset"].initial = self.PRESET_QUICKBOOKS if self.instance.column_mapping == QUICKBOOKS_MAPPING else self.PRESET_CUSTOM
    def clean(self):
        cleaned=super().clean()
        from portal.services.finance_exports import QUICKBOOKS_MAPPING, validate_export_mapping
        mapping=QUICKBOOKS_MAPPING.copy() if cleaned.get("preset")==self.PRESET_QUICKBOOKS else cleaned.get("column_mapping")
        try:validate_export_mapping(mapping)
        except ValidationError as exc:self.add_error("column_mapping",exc)
        cleaned["column_mapping"]=mapping
        return cleaned

class AccountingExportRunForm(forms.Form):
    start_date=forms.DateField(required=False,widget=forms.DateInput(attrs={"type":"date"}))
    end_date=forms.DateField(required=False,widget=forms.DateInput(attrs={"type":"date"}))
    def clean(self):
        cleaned=super().clean()
        if cleaned.get("start_date") and cleaned.get("end_date") and cleaned["start_date"]>cleaned["end_date"]:
            raise forms.ValidationError("Start date must be on or before end date.")
        return cleaned


class FinanceReportFilterForm(forms.Form):
    finance_domain=forms.ChoiceField(choices=FinanceDomain.choices,label="Finance area")
    season=forms.ModelChoiceField(queryset=Season.objects.none(),required=False,empty_label="All seasons")
    start_date=forms.DateField(required=False,widget=forms.DateInput(attrs={"type":"date"}))
    end_date=forms.DateField(required=False,widget=forms.DateInput(attrs={"type":"date"}))
    as_of=forms.DateField(required=False,widget=forms.DateInput(attrs={"type":"date"}),label="Receivables as of")
    def __init__(self,*args,team=None,allowed_domains=None,**kwargs):
        super().__init__(*args,**kwargs)
        allowed=set(allowed_domains or [])
        self.fields["finance_domain"].choices=[(v,l) for v,l in FinanceDomain.choices if v in allowed]
        self.fields["season"].queryset=Season.objects.filter(team=team).order_by("-start_date") if team else Season.objects.none()
    def clean(self):
        cleaned=super().clean()
        if cleaned.get("start_date") and cleaned.get("end_date") and cleaned["start_date"]>cleaned["end_date"]:
            raise forms.ValidationError("Start date must be on or before end date.")
        return cleaned


class BudgetForm(forms.ModelForm):
    class Meta:
        model=Budget
        fields=["name","start_date","end_date","season","status","notes"]
        widgets={"start_date":forms.DateInput(attrs={"type":"date"}),"end_date":forms.DateInput(attrs={"type":"date"}),"notes":forms.Textarea(attrs={"rows":3})}
    def __init__(self,*args,team=None,finance_domain=None,**kwargs):
        super().__init__(*args,**kwargs)
        self.team=team;self.finance_domain=finance_domain
        self.fields["season"].queryset=Season.objects.filter(team=team).order_by("-start_date") if team else Season.objects.none()
    def clean(self):
        cleaned=super().clean()
        if cleaned.get("start_date") and cleaned.get("end_date") and cleaned["end_date"]<cleaned["start_date"]:
            raise forms.ValidationError("Budget end date cannot be before the start date.")
        return cleaned


class BudgetLineForm(forms.ModelForm):
    class Meta:
        model=BudgetLine
        fields=["kind","category","description","amount","sort_order","notes"]
    def __init__(self,*args,team=None,**kwargs):
        super().__init__(*args,**kwargs)
        qs=FinancialCategory.objects.filter(team=team,active=True) if team else FinancialCategory.objects.none()
        kind=(self.data.get("kind") if self.is_bound else (self.instance.kind if self.instance and self.instance.pk else self.initial.get("kind")))
        if kind==FinancialTransaction.Kind.INCOME:qs=qs.filter(kind__in=[FinancialCategory.Kind.INCOME,FinancialCategory.Kind.BOTH])
        elif kind==FinancialTransaction.Kind.EXPENSE:qs=qs.filter(kind__in=[FinancialCategory.Kind.EXPENSE,FinancialCategory.Kind.BOTH])
        self.fields["category"].queryset=qs.order_by("sort_order","name")
