from django import template
from django.core.exceptions import ObjectDoesNotExist

from portal.view_modules.common import _can_view_family_account
from portal.view_modules.show_class_live import can_update_show_class_live_status
from portal.view_modules.show_day_live import can_update_show_live_status

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


@register.simple_tag
def show_day_schedule_rows(show, existing_rows):
    """Merge filtered rider rows with every scheduled class for the show."""
    if not show:
        return existing_rows or []

    existing_by_class_id = {
        row["class"].pk: row
        for row in (existing_rows or [])
        if row.get("class")
    }
    merged = []
    for show_class in show.classes.select_related("season_class").order_by(
        "sort_order", "class_number", "name"
    ):
        merged.append(
            existing_by_class_id.get(
                show_class.pk,
                {"class": show_class, "entries": [], "missing_results": 0},
            )
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
        return {"image": branding.upper_hero_image, "position": branding.upper_hero_image_position, "label": "Upper School Team"}
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
