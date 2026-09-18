from django import forms
from django.contrib.auth import get_user_model

from portal.model_modules.people import Person


class MyAccountForm(forms.ModelForm):
    """Canonical Person fields a signed-in user may safely maintain themselves."""

    class Meta:
        model = Person
        fields = [
            "preferred_name",
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



class EmailChangeForm(forms.Form):
    email = forms.EmailField(label="New email address")
    current_password = forms.CharField(label="Current password", widget=forms.PasswordInput)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if self.user and email == (self.user.email or "").strip().lower():
            raise forms.ValidationError("That is already your current email address.")
        users = get_user_model().objects.filter(email__iexact=email)
        if self.user:
            users = users.exclude(pk=self.user.pk)
        if users.exists():
            raise forms.ValidationError("That email address is already associated with another ArenaLine account.")
        return email

    def clean_current_password(self):
        password = self.cleaned_data.get("current_password")
        if self.user and not self.user.check_password(password):
            raise forms.ValidationError("Your current password is incorrect.")
        return password


class MFAConfirmForm(forms.Form):
    code = forms.CharField(label="6-digit authenticator code", max_length=12)


class MFADisableForm(forms.Form):
    current_password = forms.CharField(label="Current password", widget=forms.PasswordInput)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_current_password(self):
        password = self.cleaned_data.get("current_password")
        if self.user and not self.user.check_password(password):
            raise forms.ValidationError("Your current password is incorrect.")
        return password
