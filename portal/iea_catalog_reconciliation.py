"""Safe reconciliation helpers for legacy SeasonClass rows.

This module deliberately performs deterministic matching only.  It never
infers a class from display names and never mutates legacy class metadata.
"""

from dataclasses import dataclass

from .models import SeasonClass
from .model_modules.competition_iea import IEAClassCatalogEntry


SUPPORTED_DISCIPLINES = {
    IEAClassCatalogEntry.Discipline.HUNT_SEAT,
    IEAClassCatalogEntry.Discipline.WESTERN,
    IEAClassCatalogEntry.Discipline.DRESSAGE,
}


@dataclass(frozen=True)
class ReconciliationResult:
    season_class_id: int
    status: str
    catalog_entry_id: int | None = None
    reason: str = ""


def reconcile_season_class(season_class, *, rulebook_season: str, apply: bool = False):
    """Resolve one legacy SeasonClass to a catalog row when the match is exact.

    Deterministic key:
      rulebook season + discipline + normalized class code + compatible team level

    Existing links are preserved.  Names are intentionally ignored because
    historical/free-form display names are not authoritative enough for an
    automatic reconciliation.
    """
    if season_class.catalog_entry_id:
        return ReconciliationResult(
            season_class_id=season_class.pk,
            status="already_linked",
            catalog_entry_id=season_class.catalog_entry_id,
        )

    discipline = (season_class.discipline or "").strip()
    if discipline not in SUPPORTED_DISCIPLINES:
        return ReconciliationResult(
            season_class_id=season_class.pk,
            status="skipped",
            reason="unsupported_discipline",
        )

    class_code = (season_class.class_code or "").strip().upper()
    if not class_code:
        return ReconciliationResult(
            season_class_id=season_class.pk,
            status="skipped",
            reason="missing_class_code",
        )

    candidates = list(
        IEAClassCatalogEntry.objects.filter(
            rulebook_season=rulebook_season,
            discipline=discipline,
            class_code__iexact=class_code,
            active=True,
            season_assignable=True,
        )
    )

    if not candidates:
        return ReconciliationResult(
            season_class_id=season_class.pk,
            status="unmatched",
            reason="no_catalog_match",
        )

    compatible = [
        entry for entry in candidates
        if entry.team_level in {season_class.team_level, IEAClassCatalogEntry.TeamLevel.BOTH}
    ]

    if len(compatible) != 1:
        return ReconciliationResult(
            season_class_id=season_class.pk,
            status="ambiguous" if len(compatible) > 1 else "unmatched",
            reason="multiple_catalog_matches" if len(compatible) > 1 else "team_level_mismatch",
        )

    entry = compatible[0]
    if apply:
        SeasonClass.objects.filter(
            pk=season_class.pk,
            catalog_entry__isnull=True,
        ).update(catalog_entry=entry)
        season_class.catalog_entry_id = entry.pk

    return ReconciliationResult(
        season_class_id=season_class.pk,
        status="linked" if apply else "match",
        catalog_entry_id=entry.pk,
    )


def reconcile_season_classes(queryset, *, rulebook_season: str, apply: bool = False):
    return [
        reconcile_season_class(
            season_class,
            rulebook_season=rulebook_season,
            apply=apply,
        )
        for season_class in queryset.select_related("catalog_entry").order_by("pk")
    ]
