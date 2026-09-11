from django import template

from portal.view_modules.common import _can_view_family_account

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
