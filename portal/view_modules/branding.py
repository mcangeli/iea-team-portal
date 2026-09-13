"""Organization visual branding controls backed by the v2.9 Team tenant."""

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from ..branding_models import TeamBranding
from ..platform import organization_for_user
from .common import _require_manage


class TeamBrandingForm(forms.ModelForm):
    class Meta:
        model = TeamBranding
        fields = [
            "hero_image", "hero_image_position",
            "futures_hero_image", "futures_hero_image_position",
            "upper_hero_image", "upper_hero_image_position",
        ]


@login_required
def team_branding(request):
    _require_manage(request.user)
    organization = organization_for_user(request.user, required=True)
    branding, _ = TeamBranding.objects.get_or_create(team=organization)
    form = TeamBrandingForm(request.POST or None, request.FILES or None, instance=branding)
    if form.is_valid():
        form.save()
        messages.success(request, "Organization branding updated.")
        return redirect("team_branding")
    return render(request, "portal/team_branding.html", {
        "form": form,
        "organization": organization,
        "team": organization,  # Compatibility alias for the existing template contract.
        "branding": branding,
    })
