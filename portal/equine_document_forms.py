from django import forms

from .model_modules.equine_care import HorseCareRecord
from .model_modules.equine_documents import HorseDocument


class HorseDocumentForm(forms.ModelForm):
    class Meta:
        model = HorseDocument
        fields = ["document_type", "title", "file", "effective_date", "expiration_date", "care_record", "notes"]
        widgets = {
            "effective_date": forms.DateInput(attrs={"type": "date"}),
            "expiration_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, horse=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.horse = horse or (self.instance.horse if getattr(self.instance, "horse_id", None) else None)
        if self.horse is not None:
            self.instance.horse = self.horse
            self.fields["care_record"].queryset = HorseCareRecord.objects.filter(horse=self.horse).order_by("-performed_date", "-id")
        else:
            self.fields["care_record"].queryset = HorseCareRecord.objects.none()
        self.fields["care_record"].required = False
        self.fields["care_record"].label = "Related care record"

    def clean_title(self):
        return self.cleaned_data["title"].strip()

    def clean_care_record(self):
        record = self.cleaned_data.get("care_record")
        if record and self.horse and record.horse_id != self.horse.id:
            raise forms.ValidationError("Choose a care record for this horse.")
        return record
