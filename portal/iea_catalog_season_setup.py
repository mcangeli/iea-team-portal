"""Catalog-backed IEA SeasonClass generation for ArenaLine v3.0."""

from dataclasses import dataclass
from typing import Iterable

from django.db import transaction

from portal.models import SeasonClass
from portal.model_modules.competition_iea import (
    IEAClassCatalogEntry,
    IEASeasonCatalogConfiguration,
)


@dataclass(frozen=True)
class SeasonCatalogBuildResult:
    created: int
    reused: int
    linked_legacy: int
    conflicts: tuple[str, ...]


def _normalized_disciplines(values: Iterable[str]) -> list[str]:
    supported = {value for value, _label in IEAClassCatalogEntry.Discipline.choices}
    selected = []
    for value in values:
        value = (value or "").strip()
        if value in supported and value not in selected:
            selected.append(value)
    return selected


@transaction.atomic
def configure_iea_season_catalog(*, season, rulebook_season: str, disciplines: Iterable[str]):
    """Configure an ArenaLine season and create/reuse official IEA classes.

    Safety rules:
    - existing catalog-linked SeasonClass rows are reused unchanged;
    - deterministic legacy rows can be linked when discipline/code/team match;
    - no existing SeasonClass row is deleted or deactivated;
    - no legacy name, code, discipline, team level, or ordering is rewritten;
    - collisions are reported rather than guessed through.
    """

    rulebook_season = (rulebook_season or "").strip()
    selected_disciplines = _normalized_disciplines(disciplines)
    if not rulebook_season:
        raise ValueError("A rulebook season is required.")
    if not selected_disciplines:
        raise ValueError("Select at least one supported IEA discipline.")

    catalog = list(
        IEAClassCatalogEntry.objects.filter(
            rulebook_season=rulebook_season,
            discipline__in=selected_disciplines,
            active=True,
            season_assignable=True,
        ).order_by("discipline", "sort_order", "class_code")
    )
    if not catalog:
        raise ValueError("No active season-assignable catalog classes match that selection.")

    config, _created = IEASeasonCatalogConfiguration.objects.get_or_create(
        season=season,
        defaults={
            "rulebook_season": rulebook_season,
            "disciplines": selected_disciplines,
        },
    )
    config.rulebook_season = rulebook_season
    config.disciplines = selected_disciplines
    config.full_clean()
    config.save()

    created = 0
    reused = 0
    linked_legacy = 0
    conflicts: list[str] = []

    for entry in catalog:
        already = SeasonClass.objects.filter(season=season, catalog_entry=entry).first()
        if already:
            reused += 1
            continue

        legacy_candidates = list(
            SeasonClass.objects.filter(
                season=season,
                catalog_entry__isnull=True,
                discipline=entry.discipline,
                class_code__iexact=entry.class_code,
            )
        )
        compatible = [
            row for row in legacy_candidates
            if entry.team_level in {row.team_level, IEAClassCatalogEntry.TeamLevel.BOTH}
        ]

        if len(compatible) == 1:
            row = compatible[0]
            row.catalog_entry = entry
            row.save(update_fields=["catalog_entry"])
            linked_legacy += 1
            continue
        if len(compatible) > 1:
            conflicts.append(
                f"{entry.class_code}: multiple compatible legacy SeasonClass rows exist."
            )
            continue

        name_collision = SeasonClass.objects.filter(
            season=season,
            name=entry.official_name,
            team_level=entry.team_level,
        ).exists()
        if name_collision:
            conflicts.append(
                f"{entry.class_code}: a SeasonClass with the official name/team already exists but cannot be matched safely."
            )
            continue

        SeasonClass.objects.create(
            season=season,
            name=entry.official_name,
            team_level=entry.team_level,
            discipline=entry.discipline,
            sort_order=entry.sort_order,
            active=True,
            class_code=entry.class_code,
            catalog_entry=entry,
        )
        created += 1

    return SeasonCatalogBuildResult(
        created=created,
        reused=reused,
        linked_legacy=linked_legacy,
        conflicts=tuple(conflicts),
    )
