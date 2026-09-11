from django import forms

from .horse_models import Horse
from .post_show_horse_models import ShowHorseHistory, ShowHorseHistoryRecord


class ShowHorseHistoryForm(forms.ModelForm):
    class Meta:
        model = ShowHorseHistory
        fields = ["notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}


class ShowHorseHistoryRecordForm(forms.ModelForm):
    class Meta:
        model = ShowHorseHistoryRecord
        fields = [
            "horse",
            "barn_name",
            "show_name",
            "provider",
            "actually_used",
            "counted_as_contribution",
            "notes",
        ]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, history=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.history = history or getattr(self.instance, "history", None)
        if self.history:
            self.fields["horse"].queryset = Horse.objects.filter(
                team=self.history.show.team
            ).order_by("name")
            self.fields["horse"].help_text = (
                "For a leased/show-specific placeholder, select the registry horse actually used when known."
            )

    def clean(self):
        cleaned = super().clean()
        if self.history and self.history.is_final:
            raise forms.ValidationError("Final post-show horse history is locked and cannot be edited.")
        return cleaned
