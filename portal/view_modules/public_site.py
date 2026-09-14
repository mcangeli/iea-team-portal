from django.shortcuts import render
from django.utils import timezone

from portal.publication import (
    get_public_show,
    get_public_site,
    public_show_payload,
    public_show_queryset,
    public_show_schedule_payload,
    public_site_payload,
)


def _public_show_groups(site):
    today = timezone.localdate()
    shows = [public_show_payload(publication) for publication in public_show_queryset(site)]
    upcoming = [show for show in shows if show["date"] >= today]
    past = [show for show in shows if show["date"] < today]
    past.reverse()
    return upcoming, past


def public_site_home(request, site_slug):
    site = get_public_site(site_slug)
    upcoming, _past = _public_show_groups(site)
    return render(
        request,
        "public/site_home.html",
        {
            "public_site": public_site_payload(site),
            "public_shows": upcoming[:3],
            "has_more_shows": len(upcoming) > 3,
        },
    )


def public_schedule(request, site_slug):
    site = get_public_site(site_slug)
    upcoming, past = _public_show_groups(site)
    return render(
        request,
        "public/schedule.html",
        {
            "public_site": public_site_payload(site),
            "upcoming_shows": upcoming,
            "past_shows": past,
        },
    )


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
        },
    )
