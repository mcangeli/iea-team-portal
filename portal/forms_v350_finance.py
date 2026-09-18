from django import forms
from portal.model_modules.finance import AccountingExportProfile, BankImportProfile, FinanceDomain, ReceivableAccountPerson
from portal.model_modules.people import Person
from portal.models import FinancialAccount, FinancialCategory

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
    use_quickbooks_preset=forms.BooleanField(required=False,initial=True,label="Use QuickBooks-friendly columns")
    class Meta:
        model=AccountingExportProfile
        fields=["name","finance_domain","file_type","active"]
    def __init__(self,*args,allowed_domains=None,**kwargs):
        super().__init__(*args,**kwargs)
        allowed=set(allowed_domains or [])
        self.fields["finance_domain"].choices=[(v,l) for v,l in FinanceDomain.choices if v in allowed]

class AccountingExportRunForm(forms.Form):
    start_date=forms.DateField(required=False,widget=forms.DateInput(attrs={"type":"date"}))
    end_date=forms.DateField(required=False,widget=forms.DateInput(attrs={"type":"date"}))
    def clean(self):
        cleaned=super().clean()
        if cleaned.get("start_date") and cleaned.get("end_date") and cleaned["start_date"]>cleaned["end_date"]:
            raise forms.ValidationError("Start date must be on or before end date.")
        return cleaned
