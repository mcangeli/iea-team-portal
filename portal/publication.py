from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404

from portal.model_modules.public_site import PublicShowPublication, PublicSiteProfile


def get_public_site(site_slug):
    return get_object_or_404(
        PublicSiteProfile.objects.select_related("team"),
        slug=site_slug,
        enabled=True,
    )


def public_site_payload(site):
    team = site.team
    payload = {
        "slug": site.slug,
        "name": site.display_name or team.name,
        "tagline": site.tagline,
        "introduction": site.introduction,
        "logo_url": None,
        "website": None,
    }
    if site.publish_logo and team.logo:
        payload["logo_url"] = team.logo.url
    if site.publish_website and team.website:
        payload["website"] = team.website
    return payload


def public_show_queryset(site):
    return (
        PublicShowPublication.objects.select_related(
            "show", "show__season", "current_class", "current_class__season_class"
        )
        .filter(show__team=site.team, is_published=True)
        .order_by("show__show_date", "show__name")
    )


def get_public_show(site, show_slug):
    return get_object_or_404(public_show_queryset(site), slug=show_slug)


def _spectator_status_for_show(show):
    if show.status in {"planning", "registration", "entered"}:
        return "upcoming", "Upcoming"
    if show.status == "in_progress":
        return "in_progress", "In progress"
    if show.status == "paused":
        return "paused", "Paused"
    if show.status == "complete":
        return "complete", "Complete"
    if show.status == "cancelled":
        return "cancelled", "Cancelled"
    return "upcoming", "Upcoming"


def _ring_name(show_class):
    try:
        return show_class.ring_assignment.display_name
    except ObjectDoesNotExist:
        return "Main ring"


def _public_live_status(publication):
    if not publication.publish_live_status:
        return None

    code, label = _spectator_status_for_show(publication.show)
    active_classes = []
    classes = publication.show.classes.select_related(
        "season_class", "live_state", "ring_assignment"
    ).order_by("sort_order", "class_number", "name")
    for show_class in classes:
        try:
            live_state = show_class.live_state
        except ObjectDoesNotExist:
            continue
        if live_state.status not in {"in_progress", "paused"}:
            continue
        active_classes.append(
            {
                "class_number": show_class.class_number,
                "name": show_class.display_name,
                "ring": _ring_name(show_class),
                "state": live_state.status,
                "state_label": "Now" if live_state.status == "in_progress" else "Paused",
            }
        )

    current_class = publication.current_class
    return {
        "code": code,
        "label": label,
        "note": publication.public_status_note,
        "active_classes": active_classes,
        "current_class": (
            {
                "class_number": current_class.class_number,
                "name": current_class.display_name,
                "ring": _ring_name(current_class),
            }
            if current_class and current_class.show_id == publication.show_id
            else None
        ),
    }


def public_show_payload(publication):
    show = publication.show
    payload = {
        "slug": publication.slug,
        "name": show.name,
        "date": show.show_date,
        "competition_level": show.get_competition_level_display(),
        "summary": publication.public_summary,
        "time": None,
        "venue": None,
        "address": None,
        "host_team": None,
        "iea_zone": None,
        "iea_region": None,
        "live_status": _public_live_status(publication),
    }
    if publication.publish_time:
        payload["time"] = show.start_time
    if publication.publish_venue:
        payload["venue"] = show.venue
    if publication.publish_address:
        payload["address"] = show.address
    if publication.publish_host_team:
        payload["host_team"] = show.host_team
    if publication.publish_iea_area:
        payload["iea_zone"] = show.iea_zone
        payload["iea_region"] = show.iea_region
    return payload


def _class_live_public_state(show_class):
    try:
        live_state = show_class.live_state
    except ObjectDoesNotExist:
        return None

    return {
        "not_started": ("upcoming", "Upcoming"),
        "in_progress": ("current", "Now"),
        "paused": ("paused", "Paused"),
        "complete": ("complete", "Complete"),
    }.get(live_state.status)


def public_show_schedule_payload(publication):
    """Return the deliberately allow-listed public class schedule for a show."""

    if not publication.publish_schedule:
        return []

    classes = list(
        publication.show.classes.select_related(
            "season_class", "live_state", "ring_assignment"
        ).order_by("sort_order", "class_number", "name")
    )
    has_explicit_live_state = False
    for show_class in classes:
        try:
            show_class.live_state
            has_explicit_live_state = True
            break
        except ObjectDoesNotExist:
            continue

    current_index = None
    if (
        publication.publish_live_status
        and publication.current_class_id
        and not has_explicit_live_state
    ):
        for index, show_class in enumerate(classes):
            if show_class.pk == publication.current_class_id:
                current_index = index
                break

    spectator_code, _spectator_label = _spectator_status_for_show(publication.show)
    items = []
    for index, show_class in enumerate(classes):
        state = None
        state_label = None
        if publication.publish_live_status:
            explicit_state = _class_live_public_state(show_class)
            if explicit_state:
                state, state_label = explicit_state
            elif spectator_code == "complete":
                state, state_label = "complete", "Complete"
            elif spectator_code in {"upcoming", "cancelled"}:
                state, state_label = "upcoming", "Upcoming"
            elif has_explicit_live_state:
                state, state_label = "upcoming", "Upcoming"
            elif current_index is not None:
                if index < current_index:
                    state, state_label = "complete", "Complete"
                elif index == current_index:
                    if spectator_code == "paused":
                        state, state_label = "paused", "Paused"
                    else:
                        state, state_label = "current", "Now"
                else:
                    state, state_label = "upcoming", "Upcoming"

        items.append(
            {
                "class_number": show_class.class_number,
                "name": show_class.display_name,
                "ring": _ring_name(show_class),
                "time": show_class.schedule_time,
                "note": show_class.schedule_note,
                "state": state,
                "state_label": state_label,
            }
        )
    return items


def _ordinal_place(place):
    value = int(place)
    if 10 <= value % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"


def public_show_results_payload(publication):
    """Return explicitly published, allow-listed placed results grouped by class."""

    if not publication.publish_results:
        return []

    classes = publication.show.classes.select_related("season_class", "live_state").order_by(
        "sort_order", "class_number", "name"
    )
    groups = []
    for show_class in classes:
        try:
            live_state = show_class.live_state
        except ObjectDoesNotExist:
            live_state = None
        if live_state is not None and not live_state.results_published:
            continue

        entries = (
            show_class.entries.select_related("rider", "result")
            .filter(result__place__isnull=False)
            .order_by("result__place", "rider__last_name", "rider__first_name")
        )
        results = [
            {
                "place": entry.result.place,
                "place_label": _ordinal_place(entry.result.place),
                "place_class": f"place-{entry.result.place}" if 1 <= entry.result.place <= 10 else "place-other",
                "rider_name": f"{entry.rider.display_name} {entry.rider.last_name}".strip(),
            }
            for entry in entries
        ]
        if results:
            groups.append(
                {
                    "class_number": show_class.class_number,
                    "name": show_class.display_name,
                    "results": results,
                }
            )
    return groups
