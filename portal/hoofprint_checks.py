"""Operational checks for live Hoofprint data.

These checks intentionally warn rather than block finalization. Coaches and Show Leads
may need to submit a usable Hoofprint even when some registry information is incomplete.
"""


def _snapshot_comparable(payload):
    """Return only live horse-plan data that should trigger a new Hoofprint version."""
    return {
        "show": payload.get("show", {}),
        "horses": payload.get("horses", []),
    }


def live_differs_from_snapshot(live_payload, snapshot):
    if snapshot is None:
        return False
    return _snapshot_comparable(live_payload) != _snapshot_comparable(snapshot.payload or {})


def hoofprint_warnings(payload):
    warnings = []
    horses = payload.get("horses", [])
    if not horses:
        warnings.append("No available horses are currently included in the live Hoofprint.")
        return warnings

    for horse in horses:
        name = horse.get("barn_name") or horse.get("name") or "A horse"
        if not horse.get("classes"):
            warnings.append(f"{name} does not have any show classes assigned.")
        if not (horse.get("riding_description") or "").strip():
            warnings.append(f"{name} is missing a rider-facing description.")
        if horse.get("coggins_status") in {"Missing", "Expired"}:
            warnings.append(f"{name} has {horse.get('coggins_status', 'missing').lower()} Coggins information.")
        if horse.get("crop") in {"", "—"}:
            warnings.append(f"{name} is missing a crop preference.")
        if horse.get("spurs") in {"", "—"}:
            warnings.append(f"{name} is missing a spur preference.")
        if horse.get("lead_change") in {"", "—"}:
            warnings.append(f"{name} is missing lead-change information.")

    return warnings
