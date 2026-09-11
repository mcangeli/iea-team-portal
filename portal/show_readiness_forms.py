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
    """Planning form for horses the team expects to lease for one show.

    At readiness-planning time the team may only know a temporary label/provider
    and the classes the leased horse is expected to cover. Detailed horse data is
    intentionally not required because leased horses are not part of the submitted
    Hoofprint until/unless they are later added to the normal registry/show roster.
    """

    class Meta:
        model = ShowLeasedHorse
        fields = ["barn_name", "provider", "available", "show_classes", "notes"]
        labels = {
            "barn_name": "Planning name",
            "provider": "Lease source / provider",
            "available": "Count this horse as available",
            "show_classes": "Expected class coverage",
            "notes": "Planning notes",
        }
        help_texts = {
            "barn_name": "Use the horse name if known, or a temporary label such as 'Lease Horse 1'.",
            "provider": "Optional barn, owner, or organization expected to provide the horse.",
            "show_classes": "Select the classes this leased horse is expected to cover for readiness planning.",
            "notes": "Optional planning details. This information is not included on the Hoofprint.",
        }
        widgets = {
            "show_classes": forms.CheckboxSelectMultiple(),
            "notes": forms.Textarea(attrs={"rows": 3}),
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
