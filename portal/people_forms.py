from django import forms

from portal.model_modules.people import Person


class PersonForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = [
            "first_name",
            "last_name",
            "preferred_name",
            "email",
            "phone",
            "birth_date",
            "school",
            "graduation_year",
            "bio",
            "photo",
            "website_url",
            "instagram_url",
            "facebook_url",
            "tiktok_url",
            "youtube_url",
            "public_profile_enabled",
            "active",
        ]
        widgets = {
            "birth_date": forms.DateInput(attrs={"type": "date"}),
            "bio": forms.Textarea(attrs={"rows": 5}),
        }
