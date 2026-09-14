from django.shortcuts import render

from portal.publication import (
    get_public_show,
    get_public_site,
    public_show_payload,
    public_show_queryset,
    public_site_payload,
)


def public_site_home(request, site_slug):
    site = get_public_site(site_slug)
    shows = [public_show_payload(publication) for publication in public_show_queryset(site)]
    return render(
        request,
        "public/site_home.html",
        {
            "public_site": public_site_payload(site),
            "public_shows": shows,
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
        },
    )
