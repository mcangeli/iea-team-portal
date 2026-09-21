from django import forms

from .model_modules.facilities import Facility, FacilitySpace


class FacilityForm(forms.ModelForm):
    class Meta:
        model = Facility
        fields = ("name", "address", "active", "notes")
        widgets = {"notes": forms.Textarea(attrs={"rows": 4})}


class FacilitySpaceForm(forms.ModelForm):
    class Meta:
        model = FacilitySpace
        fields = (
            "parent", "name", "space_type", "reservable", "housing_capable",
            "turnout_capable", "inventory_storage_capable", "active", "notes",
        )
        widgets = {"notes": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, facility, **kwargs):
        super().__init__(*args, **kwargs)
        self.facility = facility
        parents = facility.spaces.all()
        if self.instance and self.instance.pk:
            parents = parents.exclude(pk=self.instance.pk)
        self.fields["parent"].queryset = parents.order_by("name", "id")
        self.instance.facility = facility

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.facility = self.facility
        if commit:
            obj.save()
        return obj
