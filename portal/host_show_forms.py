from django import forms

from .host_show_models import HostShowOperations


class HostShowOperationsForm(forms.ModelForm):
    class Meta:
        model = HostShowOperations
        fields = [
            "show_manager_name",
            "show_manager_email",
            "show_manager_phone",
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
