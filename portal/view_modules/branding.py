"""Team visual branding controls for v2.0 Preview 8."""

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from ..branding_models import TeamBranding
from .common import _require_manage, _team


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
    team = _team(request.user)
    branding, _ = TeamBranding.objects.get_or_create(team=team)
    form = TeamBrandingForm(request.POST or None, request.FILES or None, instance=branding)
    if form.is_valid():
        form.save()
        messages.success(request, "Team branding updated.")
        return redirect("team_branding")
    return render(request, "portal/team_branding.html", {"form": form, "team": team, "branding": branding})
