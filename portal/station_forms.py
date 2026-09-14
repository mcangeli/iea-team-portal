from django import forms

from portal.model_modules.people import OrganizationRoleAssignment, Person
from portal.model_modules.station import StationDevice, WorkShiftEntry


class StationDeviceForm(forms.ModelForm):
    class Meta:
        model = StationDevice
        fields = ["name", "notes", "active"]


class StationCredentialForm(forms.Form):
    person = forms.ModelChoiceField(queryset=Person.objects.none())
    pin = forms.CharField(
        min_length=4,
        max_length=8,
        widget=forms.PasswordInput(attrs={"inputmode": "numeric", "autocomplete": "new-password"}),
        help_text="4 to 8 digits. This PIN is separate from the person's ArenaLine password.",
    )
    active = forms.BooleanField(required=False, initial=True)

    def __init__(self, *args, team=None, person=None, **kwargs):
        super().__init__(*args, **kwargs)
        if person is not None:
            self.fields["person"].queryset = Person.objects.filter(pk=person.pk, team=person.team)
            self.fields["person"].initial = person
            self.fields["person"].disabled = True
        elif team is not None:
            self.fields["person"].queryset = Person.objects.filter(team=team, active=True).order_by(
                "last_name", "first_name"
            )

    def clean_pin(self):
        pin = (self.cleaned_data.get("pin") or "").strip()
        if not pin.isdigit():
            raise forms.ValidationError("Station PIN must contain digits only.")
        return pin


class StationActivationForm(forms.Form):
    device_key = forms.CharField(max_length=64)
    secret = forms.CharField(widget=forms.PasswordInput(attrs={"autocomplete": "off"}))


class StationPinForm(forms.Form):
    person_id = forms.IntegerField(widget=forms.HiddenInput())
    pin = forms.CharField(
        min_length=4,
        max_length=8,
        widget=forms.PasswordInput(attrs={"inputmode": "numeric", "autocomplete": "off", "autofocus": True}),
    )


STATION_ROLE_MAP = {
    OrganizationRoleAssignment.Role.WORKING_STUDENT: WorkShiftEntry.Role.WORKING_STUDENT,
    OrganizationRoleAssignment.Role.BARN_STAFF: WorkShiftEntry.Role.BARN_STAFF,
    OrganizationRoleAssignment.Role.BARN_MANAGER: WorkShiftEntry.Role.BARN_MANAGER,
    OrganizationRoleAssignment.Role.TRAINER: WorkShiftEntry.Role.TRAINER,
    OrganizationRoleAssignment.Role.ASSISTANT_TRAINER: WorkShiftEntry.Role.ASSISTANT_TRAINER,
}


class StationClockInForm(forms.Form):
    role = forms.ChoiceField(choices=())

    def __init__(self, *args, person=None, **kwargs):
        super().__init__(*args, **kwargs)
        choices = []
        if person is not None:
            active_roles = person.role_assignments.filter(active=True).values_list("role", flat=True)
            for canonical_role in active_roles:
                shift_role = STATION_ROLE_MAP.get(canonical_role)
                if shift_role:
                    choices.append((shift_role, WorkShiftEntry.Role(shift_role).label))
        self.fields["role"].choices = sorted(set(choices), key=lambda item: item[1])

    def clean_role(self):
        role = self.cleaned_data["role"]
        if role not in dict(self.fields["role"].choices):
            raise forms.ValidationError("Choose one of this person's active work roles.")
        return role
