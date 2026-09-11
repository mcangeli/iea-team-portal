from math import ceil

from .models import ShowEntry


def build_show_readiness(show):
    rides_per_horse = max(int(getattr(show.season, "rides_per_contributed_horse", 5) or 5), 1)

    active_entries = ShowEntry.objects.filter(
        show_class__show=show,
        status__in=[ShowEntry.Status.PLANNED, ShowEntry.Status.ENTERED],
    ).select_related("show_class__season_class", "rider")

    total_rides = active_entries.count()
    required_horses = ceil(total_rides / rides_per_horse) if total_rides else 0

    registry_assignments = list(
        show.horse_assignments.filter(available=True)
        .select_related("horse")
        .prefetch_related("show_classes")
    )
    leased_horses = list(
        show.leased_horses.filter(available=True).prefetch_related("show_classes")
    )
    available_horses = len(registry_assignments) + len(leased_horses)

    entered_class_ids = set(active_entries.values_list("show_class_id", flat=True))
    covered_class_ids = set()
    for assignment in registry_assignments:
        covered_class_ids.update(assignment.show_classes.values_list("id", flat=True))
    for horse in leased_horses:
        covered_class_ids.update(horse.show_classes.values_list("id", flat=True))

    uncovered = list(
        show.classes.filter(id__in=entered_class_ids - covered_class_ids)
        .select_related("season_class")
        .order_by("sort_order", "class_number", "name")
    )

    horse_shortage = max(required_horses - available_horses, 0)
    count_ready = available_horses >= required_horses
    coverage_ready = not uncovered

    return {
        "total_rides": total_rides,
        "rides_per_horse": rides_per_horse,
        "required_horses": required_horses,
        "registry_horses": len(registry_assignments),
        "leased_horses": len(leased_horses),
        "available_horses": available_horses,
        "horse_shortage": horse_shortage,
        "count_ready": count_ready,
        "coverage_ready": coverage_ready,
        "uncovered_classes": uncovered,
        "uncovered_class_count": len(uncovered),
        "ready": count_ready and coverage_ready,
    }
