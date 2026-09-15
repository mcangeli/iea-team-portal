from dataclasses import dataclass

from .model_modules.equine_care import HorseCareRecord


_STATUS_PRIORITY = {"overdue": 0, "due_soon": 1, "current": 2, "none": 3}


@dataclass(frozen=True)
class HorseCareSchedule:
    items: tuple
    overall_status: str

    @property
    def overall_status_label(self):
        return {
            "overdue": "Care overdue",
            "due_soon": "Care due soon",
            "current": "Care current",
            "none": "No scheduled care",
        }[self.overall_status]

    @property
    def urgent_items(self):
        return tuple(item for item in self.items if item.due_status in {"overdue", "due_soon"})


def care_schedule_for_horse(horse):
    """Return the latest actionable record for each generic care category.

    A newer event supersedes an older event of the same category. This avoids
    showing an old overdue farrier/dental/etc. reminder after newer care has
    already been recorded. Coggins is excluded because its dedicated model is
    the compliance source of truth. When care records are prefetched, consume
    that cache rather than issuing a query per horse in the registry.
    """
    latest_by_type = {}
    prefetched = getattr(horse, "_prefetched_objects_cache", {}).get("care_records")
    records = prefetched if prefetched is not None else horse.care_records.all()
    for record in records:
        if record.care_type == "coggins":
            continue
        current = latest_by_type.get(record.care_type)
        if current is None or (record.performed_date, record.pk) > (current.performed_date, current.pk):
            latest_by_type[record.care_type] = record

    items = [record for record in latest_by_type.values() if record.next_due_date]
    items.sort(key=lambda record: (_STATUS_PRIORITY[record.due_status], record.next_due_date, record.care_type))

    if any(record.due_status == "overdue" for record in items):
        overall = "overdue"
    elif any(record.due_status == "due_soon" for record in items):
        overall = "due_soon"
    elif items:
        overall = "current"
    else:
        overall = "none"

    return HorseCareSchedule(items=tuple(items), overall_status=overall)
