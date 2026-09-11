from django import forms
from django.contrib.auth.models import User
from django.db.models import Q

from .host_show_models import (
    HostShowDutyAssignment,
    HostShowOperations,
    HostShowReadinessCheckpoint,
    HostShowStaffAssignment,
    ShowManagerAssignment,
)


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


class HostShowReadinessCheckpointForm(forms.ModelForm):
    class Meta:
        model = HostShowReadinessCheckpoint
        fields = ["title", "due_at", "owner", "status", "notes", "sort_order"]
        widgets = {
            "due_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, team=None, **kwargs):
        super().__init__(*args, **kwargs)
        if team:
            self.fields["owner"].queryset = User.objects.filter(
                profile__team=team,
                is_active=True,
            ).order_by("last_name", "first_name", "username")


class HostShowDutyAssignmentForm(forms.ModelForm):
    class Meta:
        model = HostShowDutyAssignment
        fields = [
            "area", "title", "assigned_user", "assigned_name", "location",
            "starts_at", "ends_at", "status", "instructions", "handoff_notes",
            "relieved_by", "sort_order",
        ]
        widgets = {
            "starts_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "ends_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "instructions": forms.Textarea(attrs={"rows": 3}),
            "handoff_notes": forms.Textarea(attrs={"rows": 3}),
        }
        help_texts = {
            "assigned_user": "Choose a portal user when available.",
            "assigned_name": "Use this for a staff member or volunteer without a portal login.",
            "status": "This tracks show-day operational coverage only. It does not count toward season volunteer hours.",
        }

    def __init__(self, *args, team=None, **kwargs):
        super().__init__(*args, **kwargs)
        if team:
            users = User.objects.filter(profile__team=team, is_active=True).order_by(
                "last_name", "first_name", "username"
            )
            self.fields["assigned_user"].queryset = users
            self.fields["relieved_by"].queryset = users

    def clean(self):
        cleaned = super().clean()
        assigned_user = cleaned.get("assigned_user")
        assigned_name = (cleaned.get("assigned_name") or "").strip()
        if not assigned_user and not assigned_name:
            raise forms.ValidationError("Assign a team user or enter the staff/volunteer name.")
        return cleaned