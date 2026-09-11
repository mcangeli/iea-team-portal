from django import forms

from .models import Season, ShowClass
from .show_readiness_models import ShowLeasedHorse


class SeasonHorseRequirementForm(forms.ModelForm):
    class Meta:
        model = Season
        fields = ["rides_per_contributed_horse"]
        labels = {"rides_per_contributed_horse": "Rides per contributed horse"}
        widgets = {
            "rides_per_contributed_horse": forms.NumberInput(attrs={"min": 1, "step": 1}),
        }

    def clean_rides_per_contributed_horse(self):
        value = self.cleaned_data["rides_per_contributed_horse"]
        if value < 1:
            raise forms.ValidationError("Rides per contributed horse must be at least 1.")
        return value


class ShowLeasedHorseForm(forms.ModelForm):
    class Meta:
        model = ShowLeasedHorse
        fields = [
            "barn_name", "show_name", "provider", "available", "show_classes",
            "breed", "sex", "size_type", "height_hands",
            "crop_preference", "spur_preference", "lead_change",
            "riding_description", "restriction_notes", "coggins_status", "notes",
        ]
        widgets = {
            "show_classes": forms.CheckboxSelectMultiple(),
            "riding_description": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 3}),
            "height_hands": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }

    def __init__(self, *args, show=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.show = show
        if show:
            self.fields["show_classes"].queryset = ShowClass.objects.filter(show=show).select_related("season_class").order_by("sort_order", "class_number", "name")

    def clean_show_classes(self):
        classes = self.cleaned_data["show_classes"]
        if self.show and any(item.show_id != self.show.id for item in classes):
            raise forms.ValidationError("Classes must belong to this show.")
        return classes
