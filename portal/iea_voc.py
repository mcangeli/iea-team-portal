"""Eligibility helpers for the Hunt Seat Varsity Open Championship (VOC)."""

from dataclasses import dataclass
from decimal import Decimal

from portal.models import ShowEntry


@dataclass(frozen=True)
class VOCCandidate:
    rider_id: int
    total_points: Decimal
    h1_place: int | None
    h2_place: int | None
    cutoff_tie: bool = False


def voc_candidates(show):
    """Return ranked same-show VOC candidates from completed H1/H2 results.

    Rulebook-backed ordering uses combined H1/H2 individual points, then H1 placing.
    ArenaLine does not store the judge-card score used by IEA as the next tie-break,
    so ties still unresolved at the tenth-place cutoff are retained and flagged.
    """

    rows = list(
        ShowEntry.objects.filter(
            show_class__show=show,
            show_class__class_number__in=["H1", "H2"],
        )
        .exclude(status=ShowEntry.Status.SCRATCHED)
        .select_related("show_class", "result", "rider")
    )
    by_rider = {}
    for entry in rows:
        result = entry.result_or_none
        if not result or result.place is None:
            continue
        code = (entry.show_class.class_number or "").upper()
        by_rider.setdefault(entry.rider_id, {})[code] = entry

    ranked = []
    for rider_id, entries in by_rider.items():
        h1 = entries.get("H1")
        h2 = entries.get("H2")
        if not h1 or not h2:
            continue
        h1_result = h1.result_or_none
        h2_result = h2.result_or_none
        total = (h1_result.points or Decimal("0")) + (h2_result.points or Decimal("0"))
        ranked.append(
            VOCCandidate(
                rider_id=rider_id,
                total_points=total,
                h1_place=h1_result.place,
                h2_place=h2_result.place,
            )
        )

    ranked.sort(key=lambda row: (-row.total_points, row.h1_place or 999, row.rider_id))
    if len(ranked) <= 10:
        return ranked

    cutoff = ranked[9]
    result = list(ranked[:10])
    for row in ranked[10:]:
        if row.total_points == cutoff.total_points and row.h1_place == cutoff.h1_place:
            result.append(
                VOCCandidate(
                    rider_id=row.rider_id,
                    total_points=row.total_points,
                    h1_place=row.h1_place,
                    h2_place=row.h2_place,
                    cutoff_tie=True,
                )
            )
        else:
            break
    if len(result) > 10:
        result = [
            VOCCandidate(
                rider_id=row.rider_id,
                total_points=row.total_points,
                h1_place=row.h1_place,
                h2_place=row.h2_place,
                cutoff_tie=(
                    row.total_points == cutoff.total_points and row.h1_place == cutoff.h1_place
                ),
            )
            for row in result
        ]
    return result


def voc_candidate_ids(show):
    return [row.rider_id for row in voc_candidates(show)]
