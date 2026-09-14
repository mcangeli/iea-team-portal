from django import forms
from django.contrib.auth.models import User
from django.db.models import Q

from portal.model_modules.people import Person


class PersonForm(forms.ModelForm):
    def __init__(self, *args, team=None, **kwargs):
        super().__init__(*args, **kwargs)
        user_field = self.fields["user"]
        if team is None:
            user_field.queryset = User.objects.none()
        else:
            available = User.objects.filter(profile__team=team)
            current_user_id = getattr(self.instance, "user_id", None)
            if current_user_id:
                available = available.filter(
                    Q(arena_person__isnull=True) | Q(pk=current_user_id)
                )
            else:
                available = available.filter(arena_person__isnull=True)
            user_field.queryset = available.order_by(
                "last_name", "first_name", "username"
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
