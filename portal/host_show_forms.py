from django import forms
from django.contrib.auth.models import User

from .host_show_models import HostShowOperations, HostShowStaffAssignment, ShowManagerAssignment


class HostShowOperationsForm(forms.ModelForm):
    class Meta:
        model = HostShowOperations
        fields = [
            "venue_contact",
            "venue_contact_phone",
            "arrival_instructions",
            "check_in_location",
            "trailer_parking",
            "spectator_parking",
            "warmup_schooling",
            "ring_operations",
            "hospitality",
            "volunteer_check_in",
            "emergency_information",
            "prize_list_url",
            "schedule_url",
            "family_notes",
            "internal_notes",
        ]
        widgets = {
            "arrival_instructions": forms.Textarea(attrs={"rows": 3}),
            "trailer_parking": forms.Textarea(attrs={"rows": 3}),
            "spectator_parking": forms.Textarea(attrs={"rows": 3}),
            "warmup_schooling": forms.Textarea(attrs={"rows": 3}),
            "ring_operations": forms.Textarea(attrs={"rows": 3}),
            "hospitality": forms.Textarea(attrs={"rows": 3}),
            "volunteer_check_in": forms.Textarea(attrs={"rows": 3}),
            "emergency_information": forms.Textarea(attrs={"rows": 3}),
            "family_notes": forms.Textarea(attrs={"rows": 3}),
            "internal_notes": forms.Textarea(attrs={"rows": 4}),
        }


class ShowManagerAssignmentForm(forms.ModelForm):
    class Meta:
        model = ShowManagerAssignment
        fields = ["user", "active", "notes"]

    def __init__(self, *args, team=None, show=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.show = show or (self.instance.show if self.instance and self.instance.pk else None)
        if team:
            self.fields["user"].queryset = User.objects.filter(
                profile__team=team,
                is_active=True,
            ).order_by("last_name", "first_name", "username")

    def clean(self):
        cleaned = super().clean()
        user = cleaned.get("user")
        if self.show and user:
            duplicate = ShowManagerAssignment.objects.filter(
                show=self.show,
                user=user,
            ).exclude(pk=getattr(self.instance, "pk", None))
            if duplicate.exists():
                self.add_error("user", "This person is already assigned as a Show Manager for this show.")
        return cleaned


class HostShowStaffAssignmentForm(forms.ModelForm):
    class Meta:
        model = HostShowStaffAssignment
        fields = ["role", "name", "organization", "phone", "email", "notes", "active", "sort_order"]
