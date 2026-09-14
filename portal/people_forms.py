from django import forms
from django.contrib.auth.models import User

from portal.model_modules.people import Person


class PersonForm(forms.ModelForm):
    def __init__(self, *args, team=None, **kwargs):
        super().__init__(*args, **kwargs)
        user_field = self.fields["user"]
        if team is None:
            user_field.queryset = User.objects.none()
        else:
            user_field.queryset = (
                User.objects.filter(profile__team=team)
                .order_by("last_name", "first_name", "username")
            )
        user_field.required = False
        user_field.help_text = (
            "Optional Django login for this person. One login can be connected to only one ArenaLine Person."
        )

    class Meta:
        model = Person
        fields = [
            "user",
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
