from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import AuditEvent, Season, Show
from .show_readiness_forms import SeasonHorseRequirementForm, ShowLeasedHorseForm
from .show_readiness_models import ShowLeasedHorse
from .show_readiness_service import build_show_readiness
from .view_modules.common import _audit_event, _can_manage, _ensure_season_open, _is_show_lead, _team


def _can_manage_show_horses(user, show):
    return _can_manage(user) or _is_show_lead(user, show)


def _require_show_horse_manage(user, show):
    if not _can_manage_show_horses(user, show):
        raise PermissionDenied


@login_required
def season_horse_requirements(request, season_pk):
    if not _can_manage(request.user):
        raise PermissionDenied
    team = _team(request.user)
    season = get_object_or_404(Season, pk=season_pk, team=team)
    _ensure_season_open(season)
    form = SeasonHorseRequirementForm(request.POST or None, instance=season)
    if form.is_valid():
        season = form.save()
        _audit_event(
            team=team, actor=request.user, action=AuditEvent.Action.UPDATED,
            obj=season, season=season,
            summary=f"Updated horse contribution requirement for {season.name}",
            details={"rides_per_contributed_horse": season.rides_per_contributed_horse},
        )
        messages.success(request, "Horse contribution requirement updated.")
        return redirect("season_setup")
    return render(request, "portal/season_horse_requirements.html", {"season": season, "form": form})


@login_required
def show_readiness(request, show_pk):
    team = _team(request.user)
    show = get_object_or_404(Show.objects.select_related("season", "team"), pk=show_pk, team=team)
    readiness = build_show_readiness(show)
    leased_horses = show.leased_horses.prefetch_related("show_classes").all()
    return render(request, "portal/show_readiness.html", {
        "show": show,
        "readiness": readiness,
        "leased_horses": leased_horses,
        "can_manage_show_horses": _can_manage_show_horses(request.user, show),
        "can_manage_registry": _can_manage(request.user),
    })


@login_required
def show_leased_horse_add(request, show_pk):
    team = _team(request.user)
    show = get_object_or_404(Show.objects.select_related("season"), pk=show_pk, team=team)
    _require_show_horse_manage(request.user, show)
    _ensure_season_open(show.season)
    form = ShowLeasedHorseForm(request.POST or None, show=show)
    if form.is_valid():
        horse = form.save(commit=False)
        horse.show = show
        horse.save()
        form.save_m2m()
        _audit_event(
            team=team, actor=request.user, action=AuditEvent.Action.CREATED,
            obj=horse, season=show.season,
            summary=f"Added leased horse {horse.display_name} to {show.name}",
        )
        messages.success(request, f"Leased horse {horse.display_name} added to the show plan.")
        return redirect("show_readiness", show_pk=show.pk)
    return render(request, "portal/show_leased_horse_form.html", {"show": show, "form": form, "title": "Add leased horse"})


@login_required
def show_leased_horse_edit(request, show_pk, pk):
    team = _team(request.user)
    show = get_object_or_404(Show.objects.select_related("season"), pk=show_pk, team=team)
    _require_show_horse_manage(request.user, show)
    _ensure_season_open(show.season)
    horse = get_object_or_404(ShowLeasedHorse, pk=pk, show=show)
    form = ShowLeasedHorseForm(request.POST or None, instance=horse, show=show)
    if form.is_valid():
        horse = form.save()
        _audit_event(
            team=team, actor=request.user, action=AuditEvent.Action.UPDATED,
            obj=horse, season=show.season,
            summary=f"Updated leased horse {horse.display_name} for {show.name}",
        )
        messages.success(request, "Leased horse updated.")
        return redirect("show_readiness", show_pk=show.pk)
    return render(request, "portal/show_leased_horse_form.html", {"show": show, "horse": horse, "form": form, "title": f"Edit {horse.display_name}"})


@login_required
@require_POST
def show_leased_horse_remove(request, show_pk, pk):
    team = _team(request.user)
    show = get_object_or_404(Show.objects.select_related("season"), pk=show_pk, team=team)
    _require_show_horse_manage(request.user, show)
    _ensure_season_open(show.season)
    horse = get_object_or_404(ShowLeasedHorse, pk=pk, show=show)
    label = horse.display_name
    _audit_event(
        team=team, actor=request.user, action=AuditEvent.Action.REMOVED,
        obj=horse, season=show.season,
        summary=f"Removed leased horse {label} from {show.name}",
    )
    horse.delete()
    messages.success(request, f"{label} was removed from the leased horse list.")
    return redirect("show_readiness", show_pk=show.pk)
