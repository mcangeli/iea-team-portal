from django import forms

from .model_modules.facilities import FacilitySpace
from .model_modules.inventory import InventoryCategory, InventoryItem


class InventoryCategoryForm(forms.ModelForm):
    class Meta:
        model = InventoryCategory
        fields = ("name", "active", "notes")
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, team, **kwargs):
        super().__init__(*args, **kwargs)
        self.team = team
        self.instance.team = team

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.team = self.team
        if commit:
            obj.full_clean()
            obj.save()
        return obj


class InventoryItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = ("category", "name", "unit", "sku", "reorder_level", "active", "notes")
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, team, **kwargs):
        super().__init__(*args, **kwargs)
        self.team = team
        self.instance.team = team
        self.fields["category"].queryset = InventoryCategory.objects.filter(
            team=team, active=True
        ).order_by("name")

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.team = self.team
        if commit:
            obj.full_clean()
            obj.save()
        return obj


class InventoryMovementForm(forms.Form):
    space = forms.ModelChoiceField(queryset=FacilitySpace.objects.none(), label="Storage location")
    quantity = forms.DecimalField(min_value=0.001, max_digits=12, decimal_places=3)
    reference = forms.CharField(max_length=120, required=False)
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, team, item=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.team = team
        self.item = item
        self.fields["space"].queryset = FacilitySpace.objects.filter(
            facility__team=team, inventory_storage_capable=True, active=True
        ).select_related("facility").order_by("facility__name", "name", "id")


class InventoryAdjustmentForm(InventoryMovementForm):
    quantity = forms.DecimalField(
        min_value=0, max_digits=12, decimal_places=3, label="Physical count"
    )


class InventoryTransferForm(forms.Form):
    source_space = forms.ModelChoiceField(queryset=FacilitySpace.objects.none(), label="From")
    destination_space = forms.ModelChoiceField(queryset=FacilitySpace.objects.none(), label="To")
    quantity = forms.DecimalField(min_value=0.001, max_digits=12, decimal_places=3)
    reference = forms.CharField(max_length=120, required=False)
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, team, **kwargs):
        super().__init__(*args, **kwargs)
        spaces = FacilitySpace.objects.filter(
            facility__team=team, inventory_storage_capable=True, active=True
        ).select_related("facility").order_by("facility__name", "name", "id")
        self.fields["source_space"].queryset = spaces
        self.fields["destination_space"].queryset = spaces
