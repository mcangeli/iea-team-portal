"""Administration views for IEA catalog-backed season setup."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from ..forms import IEASeasonCatalogConfigurationForm
from ..iea_catalog_season_setup import configure_iea_season_catalog
from ..model_modules.competition_iea import IEASeasonCatalogConfiguration
from .common import _active_season, _ensure_season_open, _require_manage, _team


@login_required
def iea_catalog_configuration(request):
    _require_manage(request.user)
    team = _team(request.user)
    season = _active_season(team)
    if not season:
        messages.error(request, "Create or activate a season first.")
        return redirect("season_setup")

    _ensure_season_open(season)
    config = IEASeasonCatalogConfiguration.objects.filter(season=season).first()
    form = IEASeasonCatalogConfigurationForm(
        request.POST or None,
        initial_config=config,
    )

    if request.method == "POST" and form.is_valid():
        try:
            result = configure_iea_season_catalog(
                season=season,
                rulebook_season=form.cleaned_data["rulebook_season"],
                disciplines=form.cleaned_data["disciplines"],
            )
        except ValueError as exc:
            form.add_error(None, exc)
        else:
            summary = (
                f"Official IEA classes synchronized. {result.reused} reused · "
                f"{result.created} created · {result.linked_legacy} legacy classes linked · "
                f"{len(result.conflicts)} conflicts."
            )
            if result.conflicts:
                messages.warning(request, summary + " Review conflicts before making further class changes.")
                for conflict in result.conflicts:
                    messages.warning(request, conflict)
            else:
                messages.success(request, summary)
            return redirect("season_setup")

    return render(request, "portal/iea_catalog_configuration.html", {
        "form": form,
        "season": season,
        "config": config,
    })
