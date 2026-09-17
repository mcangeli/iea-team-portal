from django import forms


class FinanceChargeForm(forms.Form):
    description = forms.CharField(max_length=220)
    amount = forms.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    charge_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    due_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    charge_type = forms.CharField(max_length=40, required=False)
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))


class FinancePaymentForm(forms.Form):
    amount = forms.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    received_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    method = forms.CharField(max_length=40, required=False)
    reference = forms.CharField(max_length=120, required=False)
    charge_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))


class FinanceCreditForm(forms.Form):
    description = forms.CharField(max_length=220)
    amount = forms.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    credit_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    credit_type = forms.CharField(max_length=40, required=False)
    charge_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))


class FinanceAllocationForm(forms.Form):
    charge_id = forms.IntegerField()
    amount = forms.DecimalField(max_digits=12, decimal_places=2, min_value=0.01, required=False)
    notes = forms.CharField(max_length=255, required=False)
