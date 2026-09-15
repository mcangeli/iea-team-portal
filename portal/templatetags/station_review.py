from django import template

register = template.Library()


@register.filter
def attention_shifts(shifts):
    """Return Station shifts that are open or waiting for approval."""
    return [shift for shift in (shifts or []) if not shift.approved_at]


@register.filter
def approved_shifts(shifts):
    """Return approved Station shifts for the recent-work queue."""
    return [shift for shift in (shifts or []) if shift.approved_at]
