from django import forms

from .model_modules.equine_compliance_requirements import HorseComplianceRequirement


class HorseComplianceRequirementForm(forms.ModelForm):
    class Meta:
        model = HorseComplianceRequirement
        fields = ["name", "requirement_type", "document_type", "active", "notes"]
        widgets = {"notes": forms.TextInput(attrs={"placeholder": "Optional operational note"})}

    def __init__(self, *args, team=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.team = team or (self.instance.team if getattr(self.instance, "team_id", None) else None)
        if self.team is not None:
            self.instance.team = self.team
        self.fields["document_type"].required = False
        self.fields["document_type"].help_text = "Required only when the requirement is satisfied by a horse document."

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if self.team:
            qs = HorseComplianceRequirement.objects.filter(team=self.team, name__iexact=name)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("A horse compliance requirement with this name already exists.")
        return name
