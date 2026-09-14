from django import template
from django.core.exceptions import ObjectDoesNotExist

from portal.model_modules.show_day_state import SpectatorShowUpdate
from portal.models import SeasonClass
from portal.view_modules.common import _can_view_family_account
from portal.view_modules.show_class_live import can_update_show_class_live_status
from portal.view_modules.show_day_helpers import (
    _show_day_operational_levels,
    _show_day_operational_user,
)
from portal.view_modules.show_day_live import can_update_show_live_status
from portal.view_modules.spectator_updates import can_manage_spectator_updates

register = template.Library()


@register.simple_tag(takes_context=True)
def family_account_membership(context, rider, season):
    request = context.get("request")
    if not request or not season or not rider:
        return None
    membership = rider.memberships.filter(season=season).first()
    if membership and _can_view_family_account(request.user, membership):
        return membership
    return None


@register.simple_tag(takes_context=True)
def can_manage_live_show_status(context, show):
    request = context.get("request")
    if not request or not show:
        return False
    return can_update_show_live_status(request.user, show)


@register.simple_tag(takes_context=True)
def show_day_schedule_rows(context, show, existing_rows):
    """Merge scope-safe rider rows with the appropriate complete show order.

    Full-team operational users (Admin/Coach/Show Lead/Points Secretary) see every
    scheduled class, even when the organization has no rider entered. Squad-scoped
    operational users (Futures/Upper Team Parents) keep their squad boundary while
    still receiving no-entry classes explicitly linked to their squad's SeasonClass.
    Non-operational family/rider users retain a read-only view of the complete class
    order while rider/entry details remain filtered by the view layer.
    """
    if not show:
        return existing_rows or []

    existing_rows = existing_rows or []
    existing_by_class_id = {
        row["class"].pk: row
        for row in existing_rows
        if row.get("class")
    }

    request = context.get("request")
    if not request:
        return existing_rows

    operational = _show_day_operational_user(request.user, show)
    operational_levels = (
        _show_day_operational_levels(request.user, show) if operational else set()
    )

    merged = []
    for show_class in show.classes.select_related("season_class").order_by(
        "sort_order", "class_number", "name"
    ):
        existing = existing_by_class_id.get(show_class.pk)
        if existing is not None:
            merged.append(existing)
            continue

        # Full-team operators need the entire show order, independent of entries.
        if operational and operational_levels is None:
            merged.append({"class": show_class, "entries": [], "missing_results": 0})
            continue

        # Ordinary family/rider users may see the class order but not hidden rider
        # entries or live-management controls. The view layer already filtered those.
        if not operational:
            merged.append({"class": show_class, "entries": [], "missing_results": 0})
            continue

        # Squad-scoped operators may receive no-entry classes only when ArenaLine
        # has explicit season-class metadata proving the class belongs to their
        # squad. Unlinked legacy classes are not guessed into a squad.
        if operational_levels and show_class.season_class_id:
            team_level = show_class.season_class.team_level
            if (
                team_level == SeasonClass.TeamLevel.BOTH
                or team_level in operational_levels
            ):
                merged.append(
                    {"class": show_class, "entries": [], "missing_results": 0}
                )

    return merged


@register.simple_tag
def show_class_live_state(show_class):
    if not show_class:
        return None
    try:
        return show_class.live_state
    except ObjectDoesNotExist:
        return None


@register.simple_tag
def show_class_ring_name(show_class):
    if not show_class:
        return "Main ring"
    try:
        return show_class.ring_assignment.display_name
    except ObjectDoesNotExist:
        return "Main ring"


@register.simple_tag(takes_context=True)
def can_manage_live_class_status(context, show_class):
    request = context.get("request")
    if not request or not show_class:
        return False
    return can_update_show_class_live_status(request.user, show_class)


@register.simple_tag(takes_context=True)
def can_manage_spectator_show_updates(context, show):
    request = context.get("request")
    if not request or not show:
        return False
    return can_manage_spectator_updates(request.user, show)


@register.simple_tag
def show_day_rings(show):
    if not show:
        return []
    names = []
    seen = set()
    classes = show.classes.select_related("ring_assignment").order_by(
        "sort_order", "class_number", "name"
    )
    for show_class in classes:
        try:
            name = show_class.ring_assignment.display_name
        except ObjectDoesNotExist:
            name = "Main ring"
        key = name.casefold()
        if key not in seen:
            seen.add(key)
            names.append(name)
    return names


@register.simple_tag
def active_spectator_updates(show):
    if not show:
        return []
    return list(
        SpectatorShowUpdate.objects.filter(show=show, active=True)
        .select_related("created_by")
        .order_by("-updated_at", "-id")[:8]
    )


@register.simple_tag
def squad_hero(team, level):
    """Return squad-specific hero metadata, falling back to the program hero."""
    branding = getattr(team, "branding", None) if team else None
    if not branding:
        return None
    normalized = (level or "").lower()
    if "future" in normalized and branding.futures_hero_image:
        return {"image": branding.futures_hero_image, "position": branding.futures_hero_image_position, "label": "Futures Team"}
    if "upper" in normalized and branding.upper_hero_image:
        return {"image": branding.upper_hero_image, "position": branding.upper_hero_image_position, "label": "Upper Team"}
    if branding.hero_image:
        return {"image": branding.hero_image, "position": branding.hero_image_position, "label": "Team"}
    return None


@register.simple_tag
def family_squad_hero(team, rider_rows, can_manage=False):
    """Use a squad hero for a single-squad family; use program branding otherwise."""
    branding = getattr(team, "branding", None) if team else None
    if not branding:
        return None
    if not can_manage:
        levels = {
            str(row.get("membership").team_level).lower()
            for row in rider_rows
            if row.get("membership")
        }
        if len(levels) == 1:
            return squad_hero(team, next(iter(levels)))
    if branding.hero_image:
        return {"image": branding.hero_image, "position": branding.hero_image_position, "label": "Team Hub"}
    return None
