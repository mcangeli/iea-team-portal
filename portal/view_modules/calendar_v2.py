"""Calendar workspace for v2.0 Preview 5."""

import calendar as pycalendar
from datetime import date, datetime, time, timedelta
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone

from ..models import CalendarEvent, LessonGroup, SeasonClass, SeasonMembership
from .common import _can_manage, _team


def _month_start(value, fallback):
    try:
        year, month = [int(part) for part in value.split("-", 1)]
        return date(year, month, 1)
    except (AttributeError, TypeError, ValueError):
        return fallback.replace(day=1)


def _adjacent_months(selected_month):
    previous_month = (
        date(selected_month.year - 1, 12, 1)
        if selected_month.month == 1
        else date(selected_month.year, selected_month.month - 1, 1)
    )
    next_month = (
        date(selected_month.year + 1, 1, 1)
        if selected_month.month == 12
        else date(selected_month.year, selected_month.month + 1, 1)
    )
    return previous_month, next_month


def _calendar_url(month_value, view_mode, selected_kind, selected_team):
    return "{}?{}".format(
        reverse("calendar"),
        urlencode({
            "month": month_value.strftime("%Y-%m"),
            "view": view_mode,
            "kind": selected_kind,
            "team": selected_team,
        }),
    )


@login_required
def calendar(request):
    team = _team(request.user)
    if not team:
        return render(request, "portal/no_team.html")

    valid_kinds = {value for value, _label in CalendarEvent.Kind.choices}
    selected_kind = request.GET.get("kind", "all")
    if selected_kind not in valid_kinds:
        selected_kind = "all"

    selected_team = request.GET.get("team", "all").lower()
    if selected_team not in {
        "all",
        SeasonMembership.TeamLevel.FUTURES,
        SeasonMembership.TeamLevel.UPPER,
    }:
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

    events = (
        team.events.select_related("show", "lesson", "lesson__group", "season")
        .filter(starts_at__gte=start_dt, starts_at__lt=end_dt)
    )

    if not _can_manage(request.user):
        events = events.filter(visible_to_all=True)

    if selected_kind != "all":
        events = events.filter(kind=selected_kind)

    if selected_team != "all":
        show_scope = (
            Q(show__classes__season_class__team_level__in=[
                selected_team,
                SeasonClass.TeamLevel.BOTH,
            ])
            | Q(show__classes__season_class__isnull=True)
            | Q(show__classes__isnull=True)
        )
        lesson_scope = (
            Q(lesson__group__team_level__in=[
                selected_team,
                LessonGroup.TeamLevel.BOTH,
            ])
            | Q(lesson__group__isnull=True)
        )
        events = events.filter(
            (Q(kind=CalendarEvent.Kind.LESSON) & lesson_scope)
            | (Q(kind=CalendarEvent.Kind.SHOW) & show_scope)
            | ~Q(kind__in=[CalendarEvent.Kind.LESSON, CalendarEvent.Kind.SHOW])
        ).distinct()

    events = list(events.order_by("starts_at", "title")[:250])

    events_by_day = {}
    for event in events:
        local_day = timezone.localtime(event.starts_at).date()
        events_by_day.setdefault(local_day, []).append(event)

    month_weeks = []
    for week in pycalendar.Calendar(firstweekday=6).monthdatescalendar(
        selected_month.year,
        selected_month.month,
    ):
        month_weeks.append([
            {
                "date": day,
                "in_month": day.month == selected_month.month,
                "is_today": day == today,
                "events": events_by_day.get(day, []),
            }
            for day in week
        ])

    agenda_groups = [
        {"date": day, "events": events_by_day[day], "is_today": day == today}
        for day in sorted(events_by_day)
    ]

    return render(request, "portal/calendar_v2.html", {
        "events": events,
        "agenda_groups": agenda_groups,
        "month_weeks": month_weeks,
        "weekdays": ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
        "today": today,
        "selected_month": selected_month,
        "previous_month_url": _calendar_url(
            previous_month, view_mode, selected_kind, selected_team
        ),
        "next_month_url": _calendar_url(
            next_month, view_mode, selected_kind, selected_team
        ),
        "today_url": _calendar_url(
            today.replace(day=1), view_mode, selected_kind, selected_team
        ),
        "month_view_url": _calendar_url(
            selected_month, "month", selected_kind, selected_team
        ),
        "agenda_view_url": _calendar_url(
            selected_month, "agenda", selected_kind, selected_team
        ),
        "can_manage": _can_manage(request.user),
        "selected_kind": selected_kind,
        "selected_team": selected_team,
        "event_kinds": CalendarEvent.Kind.choices,
        "view_mode": view_mode,
        "view_was_explicit": view_was_explicit,
    })


@login_required
def event_detail(request, pk):
    team = _team(request.user)
    event = get_object_or_404(
        CalendarEvent.objects.select_related(
            "show", "lesson", "lesson__group", "season"
        ),
        pk=pk,
        team=team,
    )
    if not _can_manage(request.user) and not event.visible_to_all:
        raise PermissionDenied

    return render(request, "portal/calendar_event_detail_v2.html", {
        "event": event,
        "can_manage": _can_manage(request.user),
    })
