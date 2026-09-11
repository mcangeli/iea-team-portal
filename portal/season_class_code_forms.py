from django import forms

from .models import SeasonClass


class SeasonClassCodeForm(forms.ModelForm):
    class Meta:
        model = SeasonClass
        fields = ["class_code"]
        labels = {"class_code": "Class ID"}
        help_texts = {"class_code": "Use the short IEA identifier, such as H1, H2, H8, or H14."}

    def clean_class_code(self):
        return (self.cleaned_data.get("class_code") or "").strip().upper()
