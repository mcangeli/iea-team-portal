from django import forms
from django.contrib.auth.models import User

from .host_show_models import (
    HostShowDutyAssignment,
    HostShowFamilyPublication,
    HostShowOperations,
    HostShowReadinessCheckpoint,
    HostShowStaffAssignment,
    ShowManagerAssignment,
)


class HostShowOperationsForm(forms.ModelForm):
    class Meta:
        model = HostShowOperations
        fields = ["venue_contact", "venue_contact_phone", "arrival_instructions", "check_in_location", "trailer_parking", "spectator_parking", "warmup_schooling", "ring_operations", "hospitality", "volunteer_check_in", "emergency_information", "prize_list_url", "schedule_url", "family_notes", "internal_notes"]
        widgets = {name: forms.Textarea(attrs={"rows": 3}) for name in ["arrival_instructions", "trailer_parking", "spectator_parking", "warmup_schooling", "ring_operations", "hospitality", "volunteer_check_in", "emergency_information", "family_notes"]}
        widgets["internal_notes"] = forms.Textarea(attrs={"rows": 4})


class HostShowFamilyPublicationForm(forms.ModelForm):
    class Meta:
        model = HostShowFamilyPublication
        fields = ["published", "publish_arrival", "publish_parking", "publish_warmup", "publish_ring_operations", "publish_hospitality", "publish_emergency", "publish_documents", "publish_family_notes"]
        labels = {
            "published": "Publish family information",
            "publish_arrival": "Arrival & check-in",
            "publish_parking": "Trailer & spectator parking",
            "publish_warmup": "Warm-up / schooling",
            "publish_ring_operations": "Ring operations",
            "publish_hospitality": "Hospitality",
            "publish_emergency": "Emergency information",
            "publish_documents": "Prize list & published schedule links",
            "publish_family_notes": "Rider & family notes",
        }
        help_texts = {"published": "Master switch. Turning this off immediately hides the family information page without deleting the host plan."}


class ShowManagerAssignmentForm(forms.ModelForm):
    class Meta:
        model = ShowManagerAssignment
        fields = ["user", "active", "notes"]
    def __init__(self, *args, team=None, show=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.show = show or (self.instance.show if self.instance and self.instance.pk else None)
        if team:
            self.fields["user"].queryset = User.objects.filter(profile__team=team, is_active=True).order_by("last_name", "first_name", "username")
    def clean(self):
        cleaned = super().clean()
        user = cleaned.get("user")
        if self.show and user and ShowManagerAssignment.objects.filter(show=self.show, user=user).exclude(pk=getattr(self.instance, "pk", None)).exists():
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
        widgets = {"due_at": forms.DateTimeInput(attrs={"type": "datetime-local"})}
    def __init__(self, *args, team=None, **kwargs):
        super().__init__(*args, **kwargs)
        if team:
            self.fields["owner"].queryset = User.objects.filter(profile__team=team, is_active=True).order_by("last_name", "first_name", "username")


class HostShowDutyAssignmentForm(forms.ModelForm):
    class Meta:
        model = HostShowDutyAssignment
        fields = ["area", "title", "assigned_user", "assigned_name", "location", "starts_at", "ends_at", "status", "instructions", "handoff_notes", "relieved_by", "sort_order"]
        widgets = {"starts_at": forms.DateTimeInput(attrs={"type": "datetime-local"}), "ends_at": forms.DateTimeInput(attrs={"type": "datetime-local"}), "instructions": forms.Textarea(attrs={"rows": 3}), "handoff_notes": forms.Textarea(attrs={"rows": 3})}
        help_texts = {"assigned_user": "Choose a portal user when available.", "assigned_name": "Use this for a staff member or volunteer without a portal login.", "status": "This tracks show-day operational coverage only. It does not count toward season volunteer hours."}
    def __init__(self, *args, team=None, **kwargs):
        super().__init__(*args, **kwargs)
        if team:
            users = User.objects.filter(profile__team=team, is_active=True).order_by("last_name", "first_name", "username")
            self.fields["assigned_user"].queryset = users
            self.fields["relieved_by"].queryset = users
    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("assigned_user") and not (cleaned.get("assigned_name") or "").strip():
            raise forms.ValidationError("Assign a team user or enter the staff/volunteer name.")
        return cleaned
