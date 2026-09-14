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


def _public_live_status(publication):
    if not publication.publish_live_status:
        return None

    current_class = publication.current_class
    return {
        "code": publication.public_status,
        "label": publication.get_public_status_display(),
        "note": publication.public_status_note,
        "current_class": (
            {
                "class_number": current_class.class_number,
                "name": current_class.display_name,
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


def public_show_schedule_payload(publication):
    """Return the deliberately allow-listed public class schedule for a show."""

    if not publication.publish_schedule:
        return []

    classes = list(
        publication.show.classes.select_related("season_class").order_by(
            "sort_order", "class_number", "name"
        )
    )
    current_index = None
    if publication.publish_live_status and publication.current_class_id:
        for index, show_class in enumerate(classes):
            if show_class.pk == publication.current_class_id:
                current_index = index
                break

    items = []
    for index, show_class in enumerate(classes):
        state = None
        state_label = None
        if publication.publish_live_status:
            if publication.public_status == PublicShowPublication.PublicStatus.COMPLETE:
                state, state_label = "complete", "Complete"
            elif publication.public_status == PublicShowPublication.PublicStatus.UPCOMING:
                state, state_label = "upcoming", "Upcoming"
            elif current_index is not None:
                if index < current_index:
                    state, state_label = "complete", "Complete"
                elif index == current_index:
                    if publication.public_status == PublicShowPublication.PublicStatus.PAUSED:
                        state, state_label = "paused", "Paused"
                    else:
                        state, state_label = "current", "Now"
                else:
                    state, state_label = "upcoming", "Upcoming"

        items.append(
            {
                "class_number": show_class.class_number,
                "name": show_class.display_name,
                "time": show_class.schedule_time,
                "note": show_class.schedule_note,
                "state": state,
                "state_label": state_label,
            }
        )
    return items


def public_show_results_payload(publication):
    """Return allow-listed placed results grouped by class for anonymous display."""

    if not publication.publish_results:
        return []

    classes = publication.show.classes.select_related("season_class").order_by(
        "sort_order", "class_number", "name"
    )
    groups = []
    for show_class in classes:
        entries = (
            show_class.entries.select_related("rider", "result")
            .filter(result__place__isnull=False)
            .order_by("result__place", "rider__last_name", "rider__first_name")
        )
        results = [
            {
                "place": entry.result.place,
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
