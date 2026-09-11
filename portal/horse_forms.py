from django import forms

from .horse_models import Horse, HorseCogginsRecord, HorseSeasonProfile
from .models import Season, SeasonClass


class HorseForm(forms.ModelForm):
    class Meta:
        model = Horse
        fields = [
            "name", "show_name", "breed", "size_type", "height_hands",
            "has_height_restriction", "height_restriction_notes",
            "has_weight_restriction", "weight_restriction_notes",
            "crop_preference", "spur_preference", "lead_change",
            "riding_description", "ownership_type", "owner_name", "home_barn",
            "photo", "active", "notes",
        ]
        widgets = {
            "riding_description": forms.Textarea(attrs={"rows": 4}),
            "notes": forms.Textarea(attrs={"rows": 3}),
            "height_hands": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }


class HorseCogginsForm(forms.ModelForm):
    class Meta:
        model = HorseCogginsRecord
        fields = ["test_date", "expiration_date", "document", "notes"]
        widgets = {
            "test_date": forms.DateInput(attrs={"type": "date"}),
            "expiration_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class HorseSeasonProfileForm(forms.ModelForm):
    class Meta:
        model = HorseSeasonProfile
        fields = ["season", "active_for_season", "eligible_classes", "notes"]
        widgets = {
            "eligible_classes": forms.CheckboxSelectMultiple(),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, team=None, horse=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.team = team
        self.horse = horse or getattr(self.instance, "horse", None)
        if team:
            self.fields["season"].queryset = Season.objects.filter(team=team).order_by("-start_date")
        self.fields["eligible_classes"].queryset = SeasonClass.objects.none()

        season = None
        if self.is_bound:
            try:
                season_id = int(self.data.get("season", 0))
            except (TypeError, ValueError):
                season_id = 0
            if season_id and team:
                season = Season.objects.filter(pk=season_id, team=team).first()
        elif self.instance and self.instance.pk:
            season = self.instance.season

        if season:
            self.fields["eligible_classes"].queryset = SeasonClass.objects.filter(
                season=season, active=True
            ).order_by("team_level", "sort_order", "name")
        elif team:
            active = Season.objects.filter(team=team, is_active=True).order_by("-start_date").first()
            if active:
                self.fields["eligible_classes"].queryset = SeasonClass.objects.filter(
                    season=active, active=True
                ).order_by("team_level", "sort_order", "name")

    def clean_season(self):
        season = self.cleaned_data["season"]
        if self.team and season.team_id != self.team.id:
            raise forms.ValidationError("Choose a season for this team.")
        return season

    def clean_eligible_classes(self):
        classes = self.cleaned_data["eligible_classes"]
        season = self.cleaned_data.get("season")
        if season and any(item.season_id != season.id for item in classes):
            raise forms.ValidationError("Eligible classes must belong to the selected season.")
        return classes
