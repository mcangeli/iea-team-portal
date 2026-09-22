from django import forms

from .model_modules.facilities import Facility, FacilitySpace, ResourceReservation


class FacilityForm(forms.ModelForm):
    def __init__(self, *args, team, **kwargs):
        super().__init__(*args, **kwargs)
        self.team = team
        self.instance.team = team

    def clean_name(self):
        name = self.cleaned_data["name"]
        duplicates = Facility.objects.filter(team=self.team, name=name)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError("A facility with this name already exists for this organization.")
        return name

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.team = self.team
        if commit:
            obj.save()
        return obj

    class Meta:
        model = Facility
        fields = ("name", "address", "active", "notes")
        widgets = {"notes": forms.Textarea(attrs={"rows": 4})}


class FacilitySpaceForm(forms.ModelForm):
    class Meta:
        model = FacilitySpace
        fields = (
            "parent", "name", "space_type", "reservable", "housing_capable",
            "turnout_capable", "inventory_storage_capable", "active", "notes",
        )
        widgets = {"notes": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, facility, **kwargs):
        super().__init__(*args, **kwargs)
        self.facility = facility
        parents = facility.spaces.all()
        if self.instance and self.instance.pk:
            parents = parents.exclude(pk=self.instance.pk)
        self.fields["parent"].queryset = parents.order_by("name", "id")
        self.instance.facility = facility

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.facility = self.facility
        if commit:
            obj.save()
        return obj


class HorseStallAssignmentForm(forms.ModelForm):
    class Meta:
        from .model_modules.facilities import HorseStallAssignment
        model = HorseStallAssignment
        fields = ("horse", "space", "start_date", "end_date", "notes")
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, team, facility=None, moving_from=None, **kwargs):
        super().__init__(*args, **kwargs)
        from .model_modules.horses import Horse
        from .model_modules.facilities import FacilitySpace
        self.team = team
        self.moving_from = moving_from
        if moving_from is not None:
            self.instance._exclude_overlap_assignment_id = moving_from.pk
        self.fields["horse"].queryset = Horse.objects.filter(team=team, active=True).order_by("name", "id")
        spaces = FacilitySpace.objects.filter(
            facility__team=team, housing_capable=True, active=True
        ).select_related("facility", "parent")
        if facility is not None:
            spaces = spaces.filter(facility=facility)
        self.fields["space"].queryset = spaces.order_by("facility__name", "name", "id")

    def clean_horse(self):
        horse = self.cleaned_data["horse"]
        if horse.team_id != self.team.id:
            raise forms.ValidationError("Choose a horse from this organization.")
        return horse

    def clean_space(self):
        space = self.cleaned_data["space"]
        if space.facility.team_id != self.team.id:
            raise forms.ValidationError("Choose a stall from this organization.")
        if not space.housing_capable:
            raise forms.ValidationError("Choose a space that supports horse housing.")
        return space

    def clean(self):
        cleaned = super().clean()
        if self.errors:
            return cleaned
        self.instance.horse = cleaned.get("horse")
        self.instance.space = cleaned.get("space")
        self.instance.start_date = cleaned.get("start_date")
        self.instance.end_date = cleaned.get("end_date")
        self.instance.notes = cleaned.get("notes", "")
        try:
            self.instance.full_clean()
        except forms.ValidationError as exc:
            for field, errors in exc.message_dict.items():
                for error in errors:
                    self.add_error(field if field in self.fields else None, error)
        return cleaned


class HorsePastureAssignmentForm(forms.ModelForm):
    class Meta:
        from .model_modules.facilities import HorsePastureAssignment
        model = HorsePastureAssignment
        fields = ("horse", "space", "turnout_type", "start_date", "end_date", "notes")
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, team, facility=None, moving_from=None, **kwargs):
        super().__init__(*args, **kwargs)
        from .model_modules.horses import Horse
        from .model_modules.facilities import FacilitySpace
        self.team = team
        self.moving_from = moving_from
        if moving_from is not None:
            self.instance._exclude_overlap_assignment_id = moving_from.pk
        self.fields["horse"].queryset = Horse.objects.filter(team=team, active=True).order_by("name", "id")
        spaces = FacilitySpace.objects.filter(
            facility__team=team, turnout_capable=True, active=True
        ).select_related("facility", "parent")
        if facility is not None:
            spaces = spaces.filter(facility=facility)
        self.fields["space"].queryset = spaces.order_by("facility__name", "name", "id")

    def clean_horse(self):
        horse = self.cleaned_data["horse"]
        if horse.team_id != self.team.id:
            raise forms.ValidationError("Choose a horse from this organization.")
        return horse

    def clean_space(self):
        space = self.cleaned_data["space"]
        if space.facility.team_id != self.team.id:
            raise forms.ValidationError("Choose a turnout space from this organization.")
        if not space.turnout_capable:
            raise forms.ValidationError("Choose a space that supports turnout.")
        return space


class ResourceReservationForm(forms.ModelForm):
    class Meta:
        model = ResourceReservation
        fields = ("title", "starts_at", "ends_at", "notes")
        widgets = {
            "starts_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "ends_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, space, **kwargs):
        super().__init__(*args, **kwargs)
        self.space = space
        self.instance.space = space

    def clean(self):
        cleaned = super().clean()
        if self.errors:
            return cleaned
        self.instance.space = self.space
        self.instance.title = cleaned.get("title", "")
        self.instance.starts_at = cleaned.get("starts_at")
        self.instance.ends_at = cleaned.get("ends_at")
        self.instance.notes = cleaned.get("notes", "")
        starts_at = cleaned.get("starts_at")
        ends_at = cleaned.get("ends_at")
        if starts_at and ends_at:
            overlapping = ResourceReservation.objects.filter(
                space=self.space,
                starts_at__lt=ends_at,
                ends_at__gt=starts_at,
            )
            if self.instance.pk:
                overlapping = overlapping.exclude(pk=self.instance.pk)
            if overlapping.exists():
                self.add_error("starts_at", "Selected resource already has an overlapping reservation.")
                return cleaned
        try:
            self.instance.full_clean()
        except forms.ValidationError as exc:
            for field, errors in exc.message_dict.items():
                for error in errors:
                    self.add_error(field if field in self.fields else None, error)
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.space = self.space
        if commit:
            obj.save()
        return obj
