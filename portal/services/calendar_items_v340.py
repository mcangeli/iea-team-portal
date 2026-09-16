"""Unified ArenaLine calendar projections.

CalendarItem is deliberately not a model. Domain records remain authoritative and
are projected into a common read shape for calendar/agenda presentation.
"""
from dataclasses import dataclass
from datetime import datetime, time

from django.urls import reverse
from django.utils import timezone

from portal.model_modules.equine_care import HorseCareRecord
from portal.model_modules.equine_documents import HorseDocument
from portal.model_modules.horses import HorseCogginsRecord
from portal.model_modules.lessons import LegacyIEALessonOccurrenceLink, LessonOccurrence
from portal.models import CalendarEvent, SeasonClass, SeasonMembership


@dataclass(frozen=True)
class CalendarItem:
    source: str; source_id: int; category: str; kind: str; kind_label: str; title: str; starts_at: object; ends_at: object = None; location: str = ""; all_day: bool = False; url: str = ""; status: str = ""; team_level: str = ""; rsvp_requested: bool = False
    @property
    def pk(self): return self.source_id
    @property
    def get_kind_display(self): return self.kind_label


FILTER_GROUPS = (("Lessons", (("lessons", "All lessons"), ("iea_lesson", "IEA team lessons"), ("barn_lesson", "Barn lessons"))), ("Horses", (("horses", "All horse care & compliance"), ("horse_care", "Care due"), ("coggins", "Coggins expiration"), ("horse_document", "Document expiration"))), ("Competition", (("show", "Shows"),)), ("Organization", (("meeting", "Meetings"), ("deadline", "Deadlines"), ("social", "Social"), ("other", "Other"))))
FILTER_CHOICES = (("all", "All calendar items"),) + tuple(choice for _group, choices in FILTER_GROUPS for choice in choices)
VALID_FILTERS = {value for value, _label in FILTER_CHOICES}


def _date_at_midnight(value): return timezone.make_aware(datetime.combine(value, time.min), timezone.get_current_timezone())

def _manual_team_level(event):
    if event.kind == CalendarEvent.Kind.LESSON and event.lesson_id and event.lesson.group_id: return event.lesson.group.team_level
    return ""

def _manual_item(event):
    return CalendarItem(source="calendar_event", source_id=event.pk, category="lessons" if event.kind == CalendarEvent.Kind.LESSON else ("competition" if event.kind == CalendarEvent.Kind.SHOW else "organization"), kind="legacy_lesson" if event.kind == CalendarEvent.Kind.LESSON else event.kind, kind_label="Legacy IEA Lesson" if event.kind == CalendarEvent.Kind.LESSON else event.get_kind_display(), title=event.title, starts_at=event.starts_at, ends_at=event.ends_at, location=event.location, all_day=event.all_day, url=reverse("event_detail", args=[event.pk]), team_level=_manual_team_level(event), rsvp_requested=event.rsvp_requested)

def _lesson_item(occurrence):
    if occurrence.series.is_iea_series:
        context = occurrence.series.iea_context; kind, label, team_level = "iea_lesson", "IEA Team Lesson", context.team_level
    else: kind, label, team_level = "barn_lesson", "Barn Lesson", ""
    return CalendarItem(source="lesson_occurrence", source_id=occurrence.pk, category="lessons", kind=kind, kind_label=label, title=occurrence.title, starts_at=occurrence.starts_at, ends_at=occurrence.ends_at, location=occurrence.location, url=reverse("lesson_occurrence_detail", args=[occurrence.pk]), status=occurrence.status, team_level=team_level)

def _care_item(record): return CalendarItem(source="horse_care_record", source_id=record.pk, category="horses", kind="horse_care", kind_label=f"{record.get_care_type_display()} due", title=f"{record.horse.display_name} — {record.title}", starts_at=_date_at_midnight(record.next_due_date), all_day=True, url=reverse("horse_care_history", args=[record.horse_id]), status=record.due_status)
def _coggins_item(record): return CalendarItem(source="horse_coggins", source_id=record.pk, category="horses", kind="coggins", kind_label="Coggins expiration", title=f"{record.horse.display_name} — Coggins expires", starts_at=_date_at_midnight(record.expiration_date), all_day=True, url=reverse("horse_detail", args=[record.horse_id]), status=record.status)
def _document_item(document): return CalendarItem(source="horse_document", source_id=document.pk, category="horses", kind="horse_document", kind_label="Horse document expiration", title=f"{document.horse.display_name} — {document.title} expires", starts_at=_date_at_midnight(document.expiration_date), all_day=True, url=reverse("horse_detail", args=[document.horse_id]), status=document.expiration_status)

def _show_matches_team(event, selected_team):
    if event.kind != CalendarEvent.Kind.SHOW or not event.show_id: return True
    return event.show.classes.filter(season_class__team_level__in=[selected_team, SeasonClass.TeamLevel.BOTH]).exists()


def calendar_items(team, start_dt, end_dt, *, selected_kind="all", selected_team="all", include_private=False):
    """Aggregate authoritative domain records into one sorted calendar stream."""
    manual = team.events.select_related("show", "lesson", "lesson__group", "season").filter(starts_at__gte=start_dt, starts_at__lt=end_dt)
    if not include_private: manual = manual.filter(visible_to_all=True)
    converted_legacy_ids = set(LegacyIEALessonOccurrenceLink.objects.filter(legacy_lesson__team=team).values_list("legacy_lesson_id", flat=True))
    if converted_legacy_ids: manual = manual.exclude(kind=CalendarEvent.Kind.LESSON, lesson_id__in=converted_legacy_ids)
    occurrences = LessonOccurrence.objects.select_related("series__program", "series__iea_context", "series__iea_context__season").filter(series__program__team=team, starts_at__gte=start_dt, starts_at__lt=end_dt)
    start_date, end_date = timezone.localtime(start_dt).date(), timezone.localtime(end_dt).date()
    care_records = HorseCareRecord.objects.select_related("horse").filter(horse__team=team, next_due_date__gte=start_date, next_due_date__lt=end_date)
    coggins_records = HorseCogginsRecord.objects.select_related("horse").filter(horse__team=team, expiration_date__gte=start_date, expiration_date__lt=end_date)
    documents = HorseDocument.objects.select_related("horse").filter(horse__team=team, expiration_date__gte=start_date, expiration_date__lt=end_date)
    items = [_manual_item(event) for event in manual]; items.extend(_lesson_item(o) for o in occurrences); items.extend(_care_item(r) for r in care_records); items.extend(_coggins_item(r) for r in coggins_records); items.extend(_document_item(d) for d in documents)
    if selected_kind == "lessons": items = [i for i in items if i.category == "lessons"]
    elif selected_kind == "horses": items = [i for i in items if i.category == "horses"]
    elif selected_kind != "all": items = [i for i in items if i.kind == selected_kind]
    if selected_team in {SeasonMembership.TeamLevel.FUTURES, SeasonMembership.TeamLevel.UPPER}:
        filtered = []; manual_by_id = {event.pk: event for event in manual}
        for item in items:
            if item.category == "horses" or item.kind == "barn_lesson": continue
            if item.kind in {"iea_lesson", "legacy_lesson"} and item.team_level not in {selected_team, SeasonClass.TeamLevel.BOTH}: continue
            if item.kind == CalendarEvent.Kind.SHOW:
                event = manual_by_id.get(item.source_id)
                if event and not _show_matches_team(event, selected_team): continue
            filtered.append(item)
        items = filtered
    return sorted(items, key=lambda item: (item.starts_at, item.title.lower(), item.source, item.source_id))[:250]
