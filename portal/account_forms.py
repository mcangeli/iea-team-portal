from django import forms

from portal.model_modules.people import Person


class MyAccountForm(forms.ModelForm):
    """Canonical Person fields a signed-in user may safely maintain themselves."""

    class Meta:
        model = Person
        fields = [
            "preferred_name",
            "email",
            "phone",
            "school",
            "graduation_year",
            "bio",
            "photo",
            "website_url",
            "instagram_url",
            "youtube_url",
            "public_profile_enabled",
        ]
        labels = {
            "preferred_name": "Preferred name",
            "email": "Email address",
            "phone": "Phone",
            "school": "School",
            "graduation_year": "Graduation year",
            "bio": "Bio",
            "photo": "Profile photo",
            "website_url": "Website",
            "instagram_url": "Instagram",
            "youtube_url": "YouTube",
            "public_profile_enabled": "Show my approved profile information on public ArenaLine pages",
        }
        widgets = {"bio": forms.Textarea(attrs={"rows": 5})}

    def clean_email(self):
        return (self.cleaned_data.get("email") or "").strip()
