from django import template

from portal.equine_care_schedule import care_schedule_for_horse


register = template.Library()


@register.simple_tag
def horse_care_schedule(horse):
    return care_schedule_for_horse(horse)
