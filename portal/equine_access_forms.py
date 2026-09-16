from django import forms

from .model_modules.capabilities import OrganizationCapabilityAssignment


class HorseManagementCapabilityForm(forms.ModelForm):
    class Meta:
        model = OrganizationCapabilityAssignment
        fields = ["active", "start_date", "end_date", "notes"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, person=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.person = person
        self.fields["active"].label = "Manage Horses"
        self.fields["active"].help_text = (
            "Grants organization-wide horse registry, care, Coggins, document, and compliance access "
            "without changing this person's organizational role."
        )
