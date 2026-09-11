from django import forms
from django.contrib.auth.models import User


class MyAccountForm(forms.ModelForm):
    """Fields a signed-in user may safely maintain for their own login."""

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        labels = {
            "first_name": "First name",
            "last_name": "Last name",
            "email": "Email address",
        }

    def clean_email(self):
        return (self.cleaned_data.get("email") or "").strip()
