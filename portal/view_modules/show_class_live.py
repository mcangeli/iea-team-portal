from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from portal.model_modules.public_site import PublicShowPublication
from portal.model_modules.show_day_state import ShowClassLiveState, ShowClassRingAssignment
from portal.models import Show, ShowClass
from portal.platform import organization_for_view_user
from portal.view_modules.common import _can_manage, _ensure_season_open, _is_show_lead


SHOW_CLASS_LIVE_STATUS_VALUES = {value for value, _label in ShowClassLiveState.Status.choices}
ACTIVE_CLASS_STATUSES = {
    ShowClassLiveState.Status.IN_PROGRESS,
    ShowClassLiveState.Status.PAUSED,
}


def can_update_show_class_live_status(user, show_class):
    """Only organization managers and the assigned Show Lead control class state."""
    return bool(_can_manage(user) or _is_show_lead(user, show_class.show))


def _ring_name(show_class):
    try:
        return show_class.ring_assignment.display_name
    except ObjectDoesNotExist:
        return "Main ring"


def _active_ring_conflict(show_class):
    """Return another active class in this class's ring, if one exists."""
    target_ring = _ring_name(show_class).casefold()
    active_states = (
        ShowClassLiveState.objects.filter(
            show_class__show=show_class.show,
            status__in=ACTIVE_CLASS_STATUSES,
        )
        .exclude(show_class=show_class)
        .select_related("show_class", "show_class__season_class", "show_class__ring_assignment")
    )
    for state in active_states:
        if _ring_name(state.show_class).casefold() == target_ring:
            return state.show_class
    return None


@login_required
@require_POST
def show_class_ring_update(request, class_pk):
    organization = organization_for_view_user(request.user)
    show_class = get_object_or_404(
        ShowClass.objects.select_related("show", "show__season"),
        pk=class_pk,
        show__team=organization,
    )
    show = show_class.show
    _ensure_season_open(show.season)

    if not can_update_show_class_live_status(request.user, show_class):
        raise PermissionDenied

    ring = " ".join((request.POST.get("ring") or "").split())[:80]
    assignment, _created = ShowClassRingAssignment.objects.get_or_create(show_class=show_class)

    if assignment.ring != ring:
        # Do not allow moving an active class into a ring that already has another
        # active class. This preserves the one-active-class-per-ring invariant.
        original_ring = assignment.ring
        assignment.ring = ring
        conflict = _active_ring_conflict(show_class)
        if conflict:
            assignment.ring = original_ring
            messages.error(
                request,
                f"{_ring_name(conflict)} already has {conflict.display_name} active. Complete or move that class first.",
            )
            return redirect("show_day_dashboard", pk=show.pk)

        assignment.updated_by = request.user
        assignment.save()

    messages.success(request, f"{show_class.display_name} assigned to {_ring_name(show_class)}.")
    return redirect("show_day_dashboard", pk=show.pk)


@login_required
@require_POST
def show_class_live_status_update(request, class_pk):
    organization = organization_for_view_user(request.user)
    show_class = get_object_or_404(
        ShowClass.objects.select_related("show", "show__season"),
        pk=class_pk,
        show__team=organization,
    )
    show = show_class.show
    _ensure_season_open(show.season)

    if not can_update_show_class_live_status(request.user, show_class):
        raise PermissionDenied

    status = request.POST.get("status", "")
    if status not in SHOW_CLASS_LIVE_STATUS_VALUES:
        messages.error(request, "Choose a valid class status.")
        return redirect("show_day_dashboard", pk=show.pk)

    if status == ShowClassLiveState.Status.IN_PROGRESS:
        conflict = _active_ring_conflict(show_class)
        if conflict:
            messages.error(
                request,
                f"{_ring_name(show_class)} already has {conflict.display_name} active. Complete or move that class first.",
            )
            return redirect("show_day_dashboard", pk=show.pk)

    state, _created = ShowClassLiveState.objects.get_or_create(show_class=show_class)
    now = timezone.now()

    if status == ShowClassLiveState.Status.NOT_STARTED:
        state.started_at = None
        state.completed_at = None
    elif status == ShowClassLiveState.Status.IN_PROGRESS:
        if state.started_at is None:
            state.started_at = now
        state.completed_at = None
        if show.status in {
            Show.Status.PLANNING,
            Show.Status.REGISTRATION,
            Show.Status.ENTERED,
            Show.Status.PAUSED,
        }:
            show.status = Show.Status.IN_PROGRESS
            show.save(update_fields=["status"])
    elif status == ShowClassLiveState.Status.PAUSED:
        if state.started_at is None:
            state.started_at = now
        state.completed_at = None
    elif status == ShowClassLiveState.Status.COMPLETE:
        if state.started_at is None:
            state.started_at = now
        state.completed_at = now

    state.status = status
    state.updated_by = request.user
    state.save()

    publication = PublicShowPublication.objects.filter(show=show).first()
    if publication and publication.publish_live_status:
        # Keep the legacy single-current-class pointer useful for older templates,
        # while the public multi-ring payload derives every active class directly.
        if status == ShowClassLiveState.Status.IN_PROGRESS:
            publication.current_class = show_class
            publication.save(update_fields=["current_class", "updated_at"])
        elif (
            status == ShowClassLiveState.Status.COMPLETE
            and publication.current_class_id == show_class.pk
        ):
            publication.current_class = None
            publication.save(update_fields=["current_class", "updated_at"])

    messages.success(
        request,
        f"{show_class.display_name} marked {state.get_status_display().lower()} in {_ring_name(show_class)}.",
    )
    return redirect("show_day_dashboard", pk=show.pk)


@login_required
@require_POST
def show_class_results_publication_update(request, class_pk):
    organization = organization_for_view_user(request.user)
    show_class = get_object_or_404(
        ShowClass.objects.select_related("show", "show__season"),
        pk=class_pk,
        show__team=organization,
    )
    show = show_class.show
    _ensure_season_open(show.season)

    if not can_update_show_class_live_status(request.user, show_class):
        raise PermissionDenied

    state, _created = ShowClassLiveState.objects.get_or_create(show_class=show_class)
    publish = request.POST.get("publish") == "1"

    if publish:
        if state.status != ShowClassLiveState.Status.COMPLETE:
            messages.error(request, "Complete the class before publishing its results.")
            return redirect("show_day_dashboard", pk=show.pk)
        if not show_class.entries.filter(result__place__isnull=False).exists():
            messages.error(request, "Enter at least one placing before publishing results.")
            return redirect("show_day_dashboard", pk=show.pk)

        publication = PublicShowPublication.objects.filter(show=show).first()
        if not publication or not publication.is_published:
            messages.error(request, "Publish the show before publishing class results.")
            return redirect("show_day_dashboard", pk=show.pk)

        if not publication.publish_results:
            publication.publish_results = True
            publication.save(update_fields=["publish_results", "updated_at"])

    state.results_published = publish
    state.updated_by = request.user
    state.save(update_fields=["results_published", "updated_by", "updated_at"])

    messages.success(
        request,
        f"Results for {show_class.display_name} {'published' if publish else 'unpublished'}.",
    )
    return redirect("show_day_dashboard", pk=show.pk)
