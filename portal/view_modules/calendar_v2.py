"""Unified ArenaLine calendar workspace."""

import calendar as pycalendar
from datetime import date, datetime, time
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone

from ..models import CalendarEvent, SeasonMembership
from ..services.calendar_items_v340 import FILTER_GROUPS, VALID_FILTERS, calendar_items
from .common import _can_manage, _team


def _month_start(value, fallback):
    try:
        year, month = [int(part) for part in value.split("-", 1)]
        return date(year, month, 1)
    except (AttributeError, TypeError, ValueError):
        return fallback.replace(day=1)


def _adjacent_months(selected_month):
    previous_month = date(selected_month.year - 1, 12, 1) if selected_month.month == 1 else date(selected_month.year, selected_month.month - 1, 1)
    next_month = date(selected_month.year + 1, 1, 1) if selected_month.month == 12 else date(selected_month.year, selected_month.month + 1, 1)
    return previous_month, next_month


def _calendar_url(month_value, view_mode, selected_kind, selected_team):
    return "{}?{}".format(reverse("calendar"), urlencode({"month": month_value.strftime("%Y-%m"), "view": view_mode, "kind": selected_kind, "team": selected_team}))


@login_required
def calendar(request):
    team = _team(request.user)
    if not team:
        return render(request, "portal/no_team.html")
    selected_kind = request.GET.get("kind", "all")
    if selected_kind not in VALID_FILTERS:
        selected_kind = "all"
    selected_team = request.GET.get("team", "all").lower()
    if selected_team not in {"all", SeasonMembership.TeamLevel.FUTURES, SeasonMembership.TeamLevel.UPPER}:
        selected_team = "all"
    requested_view = request.GET.get("view", "")
    view_was_explicit = requested_view in {"month", "agenda"}
    view_mode = requested_view if view_was_explicit else "month"
    today = timezone.localdate()
    selected_month = _month_start(request.GET.get("month", ""), today)
    previous_month, next_month = _adjacent_months(selected_month)
    tz = timezone.get_current_timezone()
    start_dt = timezone.make_aware(datetime.combine(selected_month, time.min), tz)
    end_dt = timezone.make_aware(datetime.combine(next_month, time.min), tz)
    events = calendar_items(team, start_dt, end_dt, selected_kind=selected_kind, selected_team=selected_team, include_private=_can_manage(request.user))
    events_by_day = {}
    for event in events:
        events_by_day.setdefault(timezone.localtime(event.starts_at).date(), []).append(event)
    month_weeks = [[{"date": day, "in_month": day.month == selected_month.month, "is_today": day == today, "events": events_by_day.get(day, [])} for day in week] for week in pycalendar.Calendar(firstweekday=6).monthdatescalendar(selected_month.year, selected_month.month)]
    agenda_groups = [{"date": day, "events": events_by_day[day], "is_today": day == today} for day in sorted(events_by_day)]
    return render(request, "portal/calendar_v2.html", {
        "events": events, "agenda_groups": agenda_groups, "month_weeks": month_weeks,
        "weekdays": ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"], "today": today,
        "selected_month": selected_month,
        "previous_month_url": _calendar_url(previous_month, view_mode, selected_kind, selected_team),
        "next_month_url": _calendar_url(next_month, view_mode, selected_kind, selected_team),
        "today_url": _calendar_url(today.replace(day=1), view_mode, selected_kind, selected_team),
        "month_view_url": _calendar_url(selected_month, "month", selected_kind, selected_team),
        "agenda_view_url": _calendar_url(selected_month, "agenda", selected_kind, selected_team),
        "can_manage": _can_manage(request.user), "selected_kind": selected_kind, "selected_team": selected_team,
        "filter_groups": FILTER_GROUPS, "view_mode": view_mode, "view_was_explicit": view_was_explicit,
    })


@login_required
def event_detail(request, pk):
    team = _team(request.user)
    event = get_object_or_404(CalendarEvent.objects.select_related("show", "lesson", "lesson__group", "season"), pk=pk, team=team)
    if not _can_manage(request.user) and not event.visible_to_all:
        raise PermissionDenied
    return render(request, "portal/calendar_event_detail_v2.html", {"event": event, "can_manage": _can_manage(request.user)})
