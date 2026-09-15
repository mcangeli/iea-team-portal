from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone

from portal.public_profiles import public_profile_for_team_person, public_profiles_for_team
from portal.publication import (
    get_public_show,
    get_public_site,
    public_show_payload,
    public_show_queryset,
    public_show_results_payload,
    public_show_schedule_payload,
    public_site_payload,
)


def _public_show_groups(site):
    today = timezone.localdate()
    shows = [public_show_payload(publication) for publication in public_show_queryset(site)]
    active = [
        show
        for show in shows
        if show.get("live_status")
        and show["live_status"]["code"] in {"in_progress", "paused"}
    ]
    active_slugs = {show["slug"] for show in active}
    upcoming = [
        show
        for show in shows
        if show["date"] >= today and show["slug"] not in active_slugs
    ]
    past = [
        show
        for show in shows
        if show["date"] < today and show["slug"] not in active_slugs
    ]
    past.reverse()
    return active, upcoming, past


def public_site_home(request, site_slug):
    site = get_public_site(site_slug)
    active, upcoming, _past = _public_show_groups(site)
    preview = active + upcoming
    rider_profiles = public_profiles_for_team(site.team)
    return render(
        request,
        "public/site_home.html",
        {
            "public_site": public_site_payload(site),
            "active_shows": active,
            "public_shows": preview[:3],
            "has_more_shows": len(preview) > 3,
            "public_riders": rider_profiles[:4],
            "has_more_riders": len(rider_profiles) > 4,
        },
    )


def public_riders(request, site_slug):
    site = get_public_site(site_slug)
    return render(
        request,
        "public/riders.html",
        {
            "public_site": public_site_payload(site),
            "public_riders": public_profiles_for_team(site.team),
        },
    )


def public_rider_detail(request, site_slug, person_pk):
    site = get_public_site(site_slug)
    profile = public_profile_for_team_person(site.team, person_pk)
    if not profile:
        raise Http404
    return render(
        request,
        "public/rider_detail.html",
        {"public_site": public_site_payload(site), "public_rider": profile},
    )


def public_schedule(request, site_slug):
    site = get_public_site(site_slug)
    active, upcoming, past = _public_show_groups(site)
    return render(
        request,
        "public/schedule.html",
        {
            "public_site": public_site_payload(site),
            "active_shows": active,
            "upcoming_shows": upcoming,
            "past_shows": past,
        },
    )


def public_live_board(request, site_slug):
    """Stable spectator URL that resolves to the organization's active public show."""
    site = get_public_site(site_slug)
    for publication in public_show_queryset(site):
        payload = public_show_payload(publication)
        live_status = payload.get("live_status")
        if live_status and live_status.get("code") in {"in_progress", "paused"}:
            return redirect(
                "public_show_detail",
                site_slug=site.slug,
                show_slug=publication.slug,
            )
    return redirect("public_schedule", site_slug=site.slug)


def public_show_detail(request, site_slug, show_slug):
    site = get_public_site(site_slug)
    publication = get_public_show(site, show_slug)
    return render(
        request,
        "public/show_detail.html",
        {
            "public_site": public_site_payload(site),
            "public_show": public_show_payload(publication),
            "public_class_schedule": public_show_schedule_payload(publication),
            "public_results": public_show_results_payload(publication),
        },
    )
