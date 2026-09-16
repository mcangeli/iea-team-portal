from dataclasses import dataclass
from datetime import date, datetime, timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from portal.model_modules.lessons import LessonOccurrence, LessonSeries


@dataclass(frozen=True)
class LessonOccurrenceGenerationResult:
    created: tuple[LessonOccurrence, ...]
    existing: tuple[LessonOccurrence, ...]


def _series_schedule_window(series: LessonSeries, start_date: date, end_date: date) -> tuple[date, date] | None:
    if end_date < start_date:
        raise ValidationError("Occurrence generation end date cannot be before the start date.")
    effective_start = max(start_date, series.start_date) if series.start_date else start_date
    effective_end = min(end_date, series.end_date) if series.end_date else end_date
    if effective_end < effective_start:
        return None
    return effective_start, effective_end


def _scheduled_dates(series: LessonSeries, start_date: date, end_date: date):
    window = _series_schedule_window(series, start_date, end_date)
    if window is None:
        return
    current, effective_end = window
    days_until_weekday = (series.weekday - current.weekday()) % 7
    current += timedelta(days=days_until_weekday)
    while current <= effective_end:
        yield current
        current += timedelta(days=7)


def _aware_local_datetime(day: date, local_time):
    naive = datetime.combine(day, local_time)
    if not timezone.is_aware(naive):
        return timezone.make_aware(naive, timezone.get_current_timezone())
    return naive


def generate_lesson_occurrences(series: LessonSeries, start_date: date, end_date: date) -> LessonOccurrenceGenerationResult:
    """Materialize scheduled occurrences for a recurring LessonSeries.

    Generation is intentionally additive and idempotent. Existing occurrences are
    never rewritten from current series defaults, preserving cancellations,
    reschedules, attendance, assignments, and other operational history.
    """
    if not series.pk:
        raise ValidationError("Lesson series must be saved before generating occurrences.")
    if not series.active:
        raise ValidationError("Occurrences cannot be generated for an inactive lesson series.")
    if series.weekday is None or series.starts_at_time is None or series.duration_minutes is None:
        raise ValidationError("Lesson series requires weekday, start time, and duration before generation.")

    series.full_clean()
    created = []
    existing = []

    with transaction.atomic():
        for scheduled_date in _scheduled_dates(series, start_date, end_date):
            starts_at = _aware_local_datetime(scheduled_date, series.starts_at_time)
            occurrence = (
                LessonOccurrence.objects.select_for_update()
                .filter(series=series, starts_at=starts_at)
                .first()
            )
            if occurrence is not None:
                existing.append(occurrence)
                continue

            occurrence = LessonOccurrence(
                series=series,
                title=series.name,
                instructor=series.instructor,
                starts_at=starts_at,
                ends_at=starts_at + timedelta(minutes=series.duration_minutes),
                location=series.default_location,
                capacity=series.effective_capacity,
                status=LessonOccurrence.Status.SCHEDULED,
            )
            occurrence.full_clean()
            occurrence.save()
            created.append(occurrence)

    return LessonOccurrenceGenerationResult(tuple(created), tuple(existing))


def create_manual_lesson_occurrence(
    series: LessonSeries,
    *,
    starts_at,
    ends_at=None,
    title=None,
    instructor=None,
    location=None,
    capacity=None,
    notes="",
) -> LessonOccurrence:
    """Create a one-off occurrence without changing the recurring series schedule."""
    if not series.pk:
        raise ValidationError("Lesson series must be saved before adding an occurrence.")
    if ends_at is None:
        if series.duration_minutes is None:
            raise ValidationError("An end time or series duration is required.")
        ends_at = starts_at + timedelta(minutes=series.duration_minutes)

    occurrence = LessonOccurrence(
        series=series,
        title=title if title is not None else series.name,
        instructor=instructor if instructor is not None else series.instructor,
        starts_at=starts_at,
        ends_at=ends_at,
        location=location if location is not None else series.default_location,
        capacity=capacity if capacity is not None else series.effective_capacity,
        notes=notes,
    )
    occurrence.full_clean()
    occurrence.save()
    return occurrence
