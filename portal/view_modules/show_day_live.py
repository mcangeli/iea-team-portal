from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from portal.models import Show
from portal.platform import organization_for_view_user
from portal.view_modules.common import _can_manage, _ensure_season_open, _is_show_lead


SHOW_DAY_LIVE_STATUS_CHOICES = (
    (Show.Status.ENTERED, "Ready / upcoming"),
    (Show.Status.IN_PROGRESS, "In progress"),
    (Show.Status.PAUSED, "Paused"),
    (Show.Status.COMPLETE, "Complete"),
)
SHOW_DAY_LIVE_STATUS_VALUES = {value for value, _label in SHOW_DAY_LIVE_STATUS_CHOICES}


def can_update_show_live_status(user, show):
    """Only organization managers and the assigned Show Lead control live show state."""
    return bool(_can_manage(user) or _is_show_lead(user, show))


@login_required
@require_POST
def show_day_live_status_update(request, pk):
    organization = organization_for_view_user(request.user)
    show = get_object_or_404(
        Show.objects.select_related("season"),
        pk=pk,
        team=organization,
    )
    _ensure_season_open(show.season)

    if not can_update_show_live_status(request.user, show):
        raise PermissionDenied

    status = request.POST.get("status", "")
    if status not in SHOW_DAY_LIVE_STATUS_VALUES:
        messages.error(request, "Choose a valid show-day status.")
        return redirect("show_day_dashboard", pk=show.pk)

    if show.status != status:
        show.status = status
        show.save(update_fields=["status"])

    messages.success(request, f"Live show status updated to {show.get_status_display()}.")
    return redirect("show_day_dashboard", pk=show.pk)
