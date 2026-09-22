from django import forms

from portal.model_modules.facilities import FacilitySpace


class LessonResourceAssignmentForm(forms.Form):
    space = forms.ModelChoiceField(queryset=FacilitySpace.objects.none(), label="Managed resource")

    def __init__(self, *args, team, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["space"].queryset = FacilitySpace.objects.filter(
            facility__team=team, reservable=True, active=True
        ).select_related("facility").order_by("facility__name", "name")


class LessonResourceReleaseForm(forms.Form):
    location = forms.CharField(
        required=False,
        max_length=180,
        label="Actual location",
        help_text="Optional free-text location, for example Grass field or Outdoor schooling area.",
    )
