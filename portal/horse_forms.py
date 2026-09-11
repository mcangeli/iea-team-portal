from django import forms

from .horse_models import Horse, HorseCogginsRecord, HorseSeasonProfile, HorseShowAssignment
from .models import Season, SeasonClass, ShowClass


class HorseForm(forms.ModelForm):
    class Meta:
        model = Horse
        fields = [
            "name", "show_name", "breed", "sex", "size_type", "height_hands",
            "has_height_restriction", "height_restriction_notes",
            "has_weight_restriction", "weight_restriction_notes",
            "crop_preference", "spur_preference", "lead_change",
            "riding_description", "ownership_type", "owner_name", "home_barn",
            "photo", "active", "notes",
        ]
        widgets = {"riding_description": forms.Textarea(attrs={"rows": 4}), "notes": forms.Textarea(attrs={"rows": 3}), "height_hands": forms.NumberInput(attrs={"step": "0.01", "min": "0"})}

    def __init__(self, *args, team=None, **kwargs):
        super().__init__(*args, **kwargs)
        instance_team = self.instance.team if getattr(self.instance, "team_id", None) else None
        self.team = team or instance_team

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if self.team:
            qs = Horse.objects.filter(team=self.team, name__iexact=name)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("A horse with this name is already in the team registry.")
        return name


class HorseCogginsForm(forms.ModelForm):
    class Meta:
        model = HorseCogginsRecord
        fields = ["test_date", "expiration_date", "document", "notes"]
        widgets = {"test_date": forms.DateInput(attrs={"type": "date"}), "expiration_date": forms.DateInput(attrs={"type": "date"}), "notes": forms.Textarea(attrs={"rows": 3})}


class HorseSeasonProfileForm(forms.ModelForm):
    class Meta:
        model = HorseSeasonProfile
        fields = ["season", "active_for_season", "eligible_classes", "notes"]
        widgets = {"eligible_classes": forms.CheckboxSelectMultiple(), "notes": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, team=None, horse=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.team = team
        instance_horse = self.instance.horse if getattr(self.instance, "horse_id", None) else None
        self.horse = horse or instance_horse
        if team:
            self.fields["season"].queryset = Season.objects.filter(team=team).order_by("-start_date")
        self.fields["eligible_classes"].queryset = SeasonClass.objects.none()
        season = None
        if self.is_bound:
            try: season_id = int(self.data.get("season", 0))
            except (TypeError, ValueError): season_id = 0
            if season_id and team: season = Season.objects.filter(pk=season_id, team=team).first()
        elif self.instance and self.instance.pk: season = self.instance.season
        if season:
            self.fields["eligible_classes"].queryset = SeasonClass.objects.filter(season=season, active=True).order_by("team_level", "sort_order", "name")
        elif team:
            active = Season.objects.filter(team=team, is_active=True).order_by("-start_date").first()
            if active: self.fields["eligible_classes"].queryset = SeasonClass.objects.filter(season=active, active=True).order_by("team_level", "sort_order", "name")

    def clean_season(self):
        season = self.cleaned_data["season"]
        if self.team and season.team_id != self.team.id: raise forms.ValidationError("Choose a season for this team.")
        if self.horse and self.horse.team_id != season.team_id: raise forms.ValidationError("Horse and season must belong to the same team.")
        return season

    def clean_eligible_classes(self):
        classes = self.cleaned_data["eligible_classes"]
        season = self.cleaned_data.get("season")
        if season and any(item.season_id != season.id for item in classes): raise forms.ValidationError("Eligible classes must belong to the selected season.")
        return classes


class HorseShowAssignmentForm(forms.ModelForm):
    class Meta:
        model = HorseShowAssignment
        fields = ["horse", "available", "show_classes", "crop_preference", "spur_preference", "lead_change", "notes"]
        widgets = {"show_classes": forms.CheckboxSelectMultiple(), "notes": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, show=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.show = show
        if show:
            assigned_ids = HorseShowAssignment.objects.filter(show=show).exclude(pk=self.instance.pk).values_list("horse_id", flat=True)
            self.fields["horse"].queryset = Horse.objects.filter(team=show.team, active=True).exclude(pk__in=assigned_ids).order_by("name")
            self.fields["show_classes"].queryset = ShowClass.objects.filter(show=show).select_related("season_class").order_by("sort_order", "class_number", "name")
        self.fields["crop_preference"].choices = [("", "Use registry default")] + list(Horse.Preference.choices)
        self.fields["spur_preference"].choices = [("", "Use registry default")] + list(Horse.Preference.choices)
        self.fields["lead_change"].choices = [("", "Use registry default")] + list(Horse.LeadChange.choices)

    def clean_horse(self):
        horse = self.cleaned_data["horse"]
        if self.show and horse.team_id != self.show.team_id: raise forms.ValidationError("Choose a horse from this team.")
        return horse

    def clean_show_classes(self):
        classes = self.cleaned_data["show_classes"]
        if self.show and any(item.show_id != self.show.id for item in classes): raise forms.ValidationError("Classes must belong to this show.")
        return classes
