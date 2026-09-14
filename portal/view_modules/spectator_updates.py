from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from portal.model_modules.public_site import PublicShowPublication
from portal.model_modules.show_day_state import SpectatorShowUpdate
from portal.models import Show
from portal.platform import organization_for_view_user
from portal.view_modules.common import _can_manage, _ensure_season_open, _is_show_lead


def can_manage_spectator_updates(user, show):
    return bool(_can_manage(user) or _is_show_lead(user, show))


def _get_show_for_update(request, pk):
    organization = organization_for_view_user(request.user)
    show = get_object_or_404(
        Show.objects.select_related("season"),
        pk=pk,
        team=organization,
    )
    _ensure_season_open(show.season)
    if not can_manage_spectator_updates(request.user, show):
        raise PermissionDenied
    return show


@login_required
@require_POST
def spectator_announcement_add(request, pk):
    show = _get_show_for_update(request, pk)
    publication = PublicShowPublication.objects.filter(show=show, is_published=True).first()
    if not publication or not publication.publish_live_status:
        messages.error(request, "Enable public live status before posting spectator updates.")
        return redirect("show_day_dashboard", pk=show.pk)

    kind = request.POST.get("kind", SpectatorShowUpdate.Kind.ANNOUNCEMENT)
    valid_kinds = {value for value, _label in SpectatorShowUpdate.Kind.choices}
    if kind not in valid_kinds:
        kind = SpectatorShowUpdate.Kind.ANNOUNCEMENT

    title = " ".join((request.POST.get("title") or "").split())[:120]
    message = " ".join((request.POST.get("message") or "").split())[:280]
    ring = " ".join((request.POST.get("ring") or "").split())[:80]
    if not title:
        messages.error(request, "Enter a title for the spectator update.")
        return redirect("show_day_dashboard", pk=show.pk)

    SpectatorShowUpdate.objects.create(
        show=show,
        kind=kind,
        ring=ring,
        title=title,
        message=message,
        created_by=request.user,
    )
    messages.success(request, "Spectator update posted.")
    return redirect("show_day_dashboard", pk=show.pk)


@login_required
@require_POST
def spectator_ring_delay_update(request, pk):
    show = _get_show_for_update(request, pk)
    publication = PublicShowPublication.objects.filter(show=show, is_published=True).first()
    if not publication or not publication.publish_live_status:
        messages.error(request, "Enable public live status before posting ring delays.")
        return redirect("show_day_dashboard", pk=show.pk)

    ring = " ".join((request.POST.get("ring") or "").split())[:80] or "Main ring"
    try:
        minutes = int(request.POST.get("minutes", "0"))
    except ValueError:
        minutes = 0
    if minutes not in {0, 15, 30, 45, 60}:
        messages.error(request, "Choose a valid delay amount.")
        return redirect("show_day_dashboard", pk=show.pk)

    existing = SpectatorShowUpdate.objects.filter(
        show=show,
        kind=SpectatorShowUpdate.Kind.DELAY,
        ring__iexact=ring,
        active=True,
    )
    if minutes == 0:
        existing.update(active=False)
        messages.success(request, f"Delay cleared for {ring}.")
        return redirect("show_day_dashboard", pk=show.pk)

    existing.update(active=False)
    SpectatorShowUpdate.objects.create(
        show=show,
        kind=SpectatorShowUpdate.Kind.DELAY,
        ring=ring,
        title=f"{ring} running about {minutes} minutes behind",
        message="Published show times are estimates and may continue to change.",
        created_by=request.user,
    )
    messages.success(request, f"{minutes}-minute delay posted for {ring}.")
    return redirect("show_day_dashboard", pk=show.pk)


@login_required
@require_POST
def spectator_update_dismiss(request, update_pk):
    organization = organization_for_view_user(request.user)
    update = get_object_or_404(
        SpectatorShowUpdate.objects.select_related("show", "show__season"),
        pk=update_pk,
        show__team=organization,
    )
    _ensure_season_open(update.show.season)
    if not can_manage_spectator_updates(request.user, update.show):
        raise PermissionDenied

    update.active = False
    update.save(update_fields=["active", "updated_at"])
    messages.success(request, "Spectator update cleared.")
    return redirect("show_day_dashboard", pk=update.show_id)
