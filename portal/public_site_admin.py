from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from portal.model_modules.public_site import PublicShowPublication, PublicSiteProfile
from portal.models import Show
from portal.platform import organization_for_user
from portal.publication import public_show_payload, public_site_payload
from portal.view_modules.common import _require_manage


class PublicSiteProfileForm(forms.ModelForm):
    class Meta:
        model = PublicSiteProfile
        fields = [
            "enabled",
            "slug",
            "display_name",
            "tagline",
            "introduction",
            "publish_logo",
            "publish_website",
        ]
        help_texts = {
            "enabled": "The public site remains unavailable until this is enabled.",
            "slug": "Public URL identifier. Changing it changes the public URL.",
            "publish_logo": "Publishes the organization logo already stored in ArenaLine.",
            "publish_website": "Publishes the organization website already stored in ArenaLine.",
        }


class PublicShowPublicationForm(forms.ModelForm):
    class Meta:
        model = PublicShowPublication
        fields = [
            "is_published",
            "slug",
            "public_summary",
            "publish_time",
            "publish_venue",
            "publish_address",
            "publish_host_team",
            "publish_iea_area",
            "publish_schedule",
        ]
        help_texts = {
            "is_published": "The show is public only when both this and the organization public site are enabled.",
            "slug": "Public URL identifier for this show.",
            "public_summary": "Optional public-facing summary. Private show notes are never copied here automatically.",
            "publish_schedule": "Publishes only class order, class number/name, public schedule time, and schedule note. Rider entries and internal strategy stay private.",
        }


def _default_site_slug(organization):
    base = slugify(organization.short_name or organization.name) or f"organization-{organization.pk}"
    candidate = base
    suffix = 2
    while PublicSiteProfile.objects.filter(slug=candidate).exclude(team=organization).exists():
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def _default_show_slug(show):
    base = slugify(f"{show.show_date.isoformat()}-{show.name}") or f"show-{show.pk}"
    candidate = base
    suffix = 2
    while PublicShowPublication.objects.filter(slug=candidate).exclude(show=show).exists():
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


@login_required
def public_site_manage(request):
    _require_manage(request.user)
    organization = organization_for_user(request.user, required=True)
    profile, _ = PublicSiteProfile.objects.get_or_create(
        team=organization,
        defaults={"slug": _default_site_slug(organization)},
    )
    form = PublicSiteProfileForm(request.POST or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        profile = form.save()
        messages.success(request, "Public site settings updated.")
        return redirect("public_site_manage")

    shows = Show.objects.filter(team=organization).select_related("season").order_by("-show_date", "name")
    rows = []
    publications = {
        item.show_id: item
        for item in PublicShowPublication.objects.filter(show__team=organization).select_related("show")
    }
    for show in shows:
        publication = publications.get(show.pk)
        rows.append({
            "show": show,
            "publication": publication,
            "is_published": bool(publication and publication.is_published),
        })

    return render(request, "portal/public_site_manage.html", {
        "form": form,
        "profile": profile,
        "organization": organization,
        "rows": rows,
        "preview_site": public_site_payload(profile),
    })


@login_required
def public_show_publication_edit(request, show_pk):
    _require_manage(request.user)
    organization = organization_for_user(request.user, required=True)
    show = get_object_or_404(Show, pk=show_pk, team=organization)
    publication, _ = PublicShowPublication.objects.get_or_create(
        show=show,
        defaults={"slug": _default_show_slug(show)},
    )
    form = PublicShowPublicationForm(request.POST or None, instance=publication)
    if request.method == "POST" and form.is_valid():
        publication = form.save()
        messages.success(request, f"Public settings updated for {show.name}.")
        return redirect("public_site_manage")

    return render(request, "portal/public_show_publication_form.html", {
        "form": form,
        "show": show,
        "publication": publication,
        "preview_show": public_show_payload(publication),
    })
