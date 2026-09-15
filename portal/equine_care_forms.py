from django import forms

from .model_modules.equine_care import HorseCareRecord
from .model_modules.people import Person


class HorseCareRecordForm(forms.ModelForm):
    class Meta:
        model = HorseCareRecord
        fields = ["care_type", "title", "performed_date", "next_due_date", "provider", "notes"]
        widgets = {
            "performed_date": forms.DateInput(attrs={"type": "date"}),
            "next_due_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, team=None, horse=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.team = team
        self.horse = horse or (self.instance.horse if getattr(self.instance, "horse_id", None) else None)
        if self.horse is not None:
            self.instance.horse = self.horse
        self.fields["provider"].queryset = (
            Person.objects.filter(team=team, active=True).order_by("last_name", "first_name")
            if team is not None else Person.objects.none()
        )
        self.fields["provider"].required = False

    def clean_title(self):
        return self.cleaned_data["title"].strip()

    def clean_provider(self):
        provider = self.cleaned_data.get("provider")
        if provider and self.team and provider.team_id != self.team.id:
            raise forms.ValidationError("Choose a care provider from this organization.")
        return provider
