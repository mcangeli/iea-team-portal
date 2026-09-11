from pathlib import Path

from django import forms

from .hoofprint_models import ShowHorseListDocument


class HoofprintFinalizeForm(forms.Form):
    coach_name = forms.CharField(max_length=160, required=False, label="Coach name")
    coach_phone = forms.CharField(max_length=40, required=False, label="Coach phone")
    horses_contributed = forms.IntegerField(min_value=0, required=False, label="Horses contributed")
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}), label="Submission notes")

    def __init__(self, *args, show=None, **kwargs):
        super().__init__(*args, **kwargs)
        if show and not self.is_bound:
            self.fields["horses_contributed"].initial = show.horse_assignments.filter(available=True).count()


class ShowHorseListDocumentForm(forms.ModelForm):
    class Meta:
        model = ShowHorseListDocument
        fields = ["document", "source_name", "notes"]
        labels = {
            "document": "Photo or PDF of horse list",
            "source_name": "Source / host team",
            "notes": "Notes",
        }
        help_texts = {
            "document": "Take a clear photo of the printed horse list with your phone, or upload a PDF/image you received electronically.",
            "source_name": "Optional. Example: host barn or show office.",
            "notes": "Optional note about this revision.",
        }
        widgets = {
            "document": forms.ClearableFileInput(attrs={"accept": "image/*,application/pdf", "capture": "environment"}),
            "notes": forms.TextInput(attrs={"maxlength": 255}),
        }

    def clean_document(self):
        document = self.cleaned_data["document"]
        suffix = Path(document.name).suffix.lower()
        allowed = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".pdf"}
        if suffix not in allowed:
            raise forms.ValidationError("Upload a photo (JPG, PNG, WEBP, HEIC) or PDF.")
        if document.size > 20 * 1024 * 1024:
            raise forms.ValidationError("The horse list file must be 20 MB or smaller.")
        return document
