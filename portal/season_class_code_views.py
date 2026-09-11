from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from .models import SeasonClass
from .season_class_code_forms import SeasonClassCodeForm
from .view_modules.common import _can_manage, _ensure_season_open, _team


@login_required
def season_class_code_edit(request, class_pk):
    if not _can_manage(request.user):
        raise PermissionDenied
    team = _team(request.user)
    season_class = get_object_or_404(
        SeasonClass.objects.select_related("season", "season__team"),
        pk=class_pk,
        season__team=team,
    )
    _ensure_season_open(season_class.season)
    form = SeasonClassCodeForm(request.POST or None, instance=season_class)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Class ID for {season_class.name} updated to {season_class.class_code or 'blank'}.")
        return redirect("season_setup")
    return render(request, "portal/season_class_code_form.html", {
        "form": form,
        "season_class": season_class,
    })
