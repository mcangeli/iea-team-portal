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
