from django import forms
from portal.model_modules.finance import FinanceDomain, ReceivableAccountPerson
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
