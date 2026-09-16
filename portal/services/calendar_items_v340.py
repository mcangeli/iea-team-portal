"""Unified ArenaLine calendar projections.

CalendarItem is deliberately not a model. Domain records remain authoritative and
are projected into a common read shape for calendar/agenda presentation.
"""
from dataclasses import dataclass

from django.urls import reverse

from portal.model_modules.lessons import LessonOccurrence
from portal.models import CalendarEvent, SeasonMembership


@dataclass(frozen=True)
class CalendarItem:
    source: str
    source_id: int
    category: str
    kind: str
    kind_label: str
    title: str
    starts_at: object
    ends_at: object = None
    location: str = ""
    all_day: bool = False
    url: str = ""
    status: str = ""
    team_level: str = ""
    rsvp_requested: bool = False

    @property
    def pk(self):
        return self.source_id

    @property
    def get_kind_display(self):
        return self.kind_label


FILTER_CHOICES = (
    ("all", "All calendar items"),
    ("lessons", "All lessons"),
    ("iea_lesson", "IEA team lessons"),
    ("barn_lesson", "Barn lessons"),
    ("show", "Shows"),
    ("meeting", "Meetings"),
    ("deadline", "Deadlines"),
    ("social", "Social"),
    ("other", "Other"),
)
VALID_FILTERS = {value for value, _label in FILTER_CHOICES}


def _manual_item(event):
    return CalendarItem(
        source="calendar_event",
        source_id=event.pk,
        category="competition" if event.kind == CalendarEvent.Kind.SHOW else "organization",
        kind=event.kind,
        kind_label=event.get_kind_display(),
        title=event.title,
        starts_at=event.starts_at,
        ends_at=event.ends_at,
        location=event.location,
        all_day=event.all_day,
        url=reverse("event_detail", args=[event.pk]),
        rsvp_requested=event.rsvp_requested,
    )


def _lesson_item(occurrence):
    if occurrence.series.is_iea_series:
        context = occurrence.series.iea_context
        kind = "iea_lesson"
        label = "IEA Team Lesson"
        team_level = context.team_level
    else:
        kind = "barn_lesson"
        label = "Barn Lesson"
        team_level = ""
    return CalendarItem(
        source="lesson_occurrence",
        source_id=occurrence.pk,
        category="lessons",
        kind=kind,
        kind_label=label,
        title=occurrence.title,
        starts_at=occurrence.starts_at,
        ends_at=occurrence.ends_at,
        location=occurrence.location,
        url=reverse("lesson_occurrence_detail", args=[occurrence.pk]),
        status=occurrence.status,
        team_level=team_level,
    )


def calendar_items(team, start_dt, end_dt, *, selected_kind="all", selected_team="all", include_private=False):
    """Aggregate authoritative domain records into one sorted calendar stream."""
    manual = team.events.select_related("show", "lesson", "lesson__group", "season").filter(
        starts_at__gte=start_dt,
        starts_at__lt=end_dt,
    )
    if not include_private:
        manual = manual.filter(visible_to_all=True)

    # v3.4 LessonOccurrence replaces legacy CalendarEvent lesson projection. Keep
    # legacy lesson events only for records not yet represented in the new domain.
    manual = manual.exclude(kind=CalendarEvent.Kind.LESSON)

    occurrences = LessonOccurrence.objects.select_related(
        "series__program", "series__iea_context", "series__iea_context__season"
    ).filter(
        series__program__team=team,
        starts_at__gte=start_dt,
        starts_at__lt=end_dt,
    )

    items = [_manual_item(event) for event in manual]
    items.extend(_lesson_item(occurrence) for occurrence in occurrences)

    if selected_kind == "lessons":
        items = [item for item in items if item.category == "lessons"]
    elif selected_kind != "all":
        items = [item for item in items if item.kind == selected_kind]

    if selected_team in {SeasonMembership.TeamLevel.FUTURES, SeasonMembership.TeamLevel.UPPER}:
        # Barn lessons are organization-wide, not IEA team-level records.
        items = [
            item for item in items
            if item.kind != "barn_lesson"
            and (item.kind != "iea_lesson" or item.team_level == selected_team)
        ]

    return sorted(items, key=lambda item: (item.starts_at, item.title.lower(), item.source, item.source_id))[:250]
