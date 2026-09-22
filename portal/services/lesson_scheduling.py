from dataclasses import dataclass
from datetime import date, datetime, timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from portal.model_modules.lessons import LessonOccurrence, LessonSeries
from portal.services.lesson_resources import current_lesson_resource_reservation, release_lesson_resource, sync_lesson_resource_times


@dataclass(frozen=True)
class LessonOccurrenceGenerationResult:
    created: tuple[LessonOccurrence, ...]
    existing: tuple[LessonOccurrence, ...]


@dataclass(frozen=True)
class LessonOccurrenceRefreshResult:
    updated: tuple[LessonOccurrence, ...]
    preserved: tuple[LessonOccurrence, ...]


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


def _validate_series_for_generation(series: LessonSeries):
    if not series.pk:
        raise ValidationError("Lesson series must be saved before generating occurrences.")
    if not series.active:
        raise ValidationError("Occurrences cannot be generated for an inactive lesson series.")
    if series.weekday is None or series.starts_at_time is None or series.duration_minutes is None:
        raise ValidationError("Lesson series requires weekday, start time, and duration before generation.")
    series.full_clean()


def _occurrence_has_operational_history(occurrence: LessonOccurrence) -> bool:
    return occurrence.attendance_records.exists() or occurrence.assignments.exists()


def generate_lesson_occurrences(series: LessonSeries, start_date: date, end_date: date) -> LessonOccurrenceGenerationResult:
    """Materialize recurring slots using immutable schedule identity.

    `scheduled_for` is the original recurrence slot. A reschedule changes only
    `starts_at`/`ends_at`, so a later generator run finds the same occurrence and
    cannot recreate the old slot.
    """
    _validate_series_for_generation(series)
    created = []
    existing = []

    with transaction.atomic():
        for scheduled_date in _scheduled_dates(series, start_date, end_date):
            scheduled_for = _aware_local_datetime(scheduled_date, series.starts_at_time)
            occurrence = (
                LessonOccurrence.objects.select_for_update()
                .filter(series=series, scheduled_for=scheduled_for)
                .first()
            )
            if occurrence is not None:
                existing.append(occurrence)
                continue

            occurrence = LessonOccurrence(
                series=series,
                title=series.name,
                instructor=series.instructor,
                starts_at=scheduled_for,
                ends_at=scheduled_for + timedelta(minutes=series.duration_minutes),
                origin=LessonOccurrence.Origin.GENERATED,
                scheduled_for=scheduled_for,
                location=series.default_location,
                capacity=series.effective_capacity,
                status=LessonOccurrence.Status.SCHEDULED,
            )
            occurrence.full_clean()
            occurrence.save()
            created.append(occurrence)

    return LessonOccurrenceGenerationResult(tuple(created), tuple(existing))


def refresh_future_lesson_occurrences(series: LessonSeries, *, from_datetime=None) -> LessonOccurrenceRefreshResult:
    _validate_series_for_generation(series)
    cutoff = from_datetime or timezone.now()
    if timezone.is_naive(cutoff):
        cutoff = timezone.make_aware(cutoff, timezone.get_current_timezone())

    updated = []
    preserved = []
    with transaction.atomic():
        occurrences = LessonOccurrence.objects.select_for_update().filter(series=series, starts_at__gte=cutoff).order_by("starts_at", "id")
        for occurrence in occurrences:
            if occurrence.status != LessonOccurrence.Status.SCHEDULED or _occurrence_has_operational_history(occurrence):
                preserved.append(occurrence)
                continue
            occurrence.title = series.name
            occurrence.instructor = series.instructor
            occurrence.ends_at = occurrence.starts_at + timedelta(minutes=series.duration_minutes)
            occurrence.location = series.default_location
            occurrence.capacity = series.effective_capacity
            occurrence.full_clean()
            occurrence.save()
            updated.append(occurrence)
    return LessonOccurrenceRefreshResult(tuple(updated), tuple(preserved))


def cancel_lesson_occurrence(occurrence: LessonOccurrence, *, notes=None) -> LessonOccurrence:
    if occurrence.status == LessonOccurrence.Status.COMPLETED:
        raise ValidationError("A completed lesson occurrence cannot be cancelled.")
    occurrence.status = LessonOccurrence.Status.CANCELLED
    if notes is not None:
        occurrence.notes = notes
    occurrence.full_clean()
    occurrence.save()
    release_lesson_resource(occurrence, location=occurrence.location)
    return occurrence


def reschedule_lesson_occurrence(occurrence: LessonOccurrence, *, starts_at, ends_at=None, notes=None) -> LessonOccurrence:
    """Move one occurrence while retaining its immutable generated slot."""
    if occurrence.status == LessonOccurrence.Status.COMPLETED:
        raise ValidationError("A completed lesson occurrence cannot be rescheduled.")
    if ends_at is None:
        duration = occurrence.ends_at - occurrence.starts_at if occurrence.ends_at else None
        if duration is None:
            raise ValidationError("An end time is required when the occurrence has no existing duration.")
        ends_at = starts_at + duration
    occurrence.starts_at = starts_at
    occurrence.ends_at = ends_at
    occurrence.status = LessonOccurrence.Status.RESCHEDULED
    if notes is not None:
        occurrence.notes = notes
    occurrence.full_clean()
    reservation = current_lesson_resource_reservation(occurrence)
    if reservation:
        original_starts_at, original_ends_at = occurrence.starts_at, occurrence.ends_at
        try:
            sync_lesson_resource_times(occurrence)
        except ValidationError:
            occurrence.refresh_from_db()
            raise
    occurrence.save()
    return occurrence


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
        origin=LessonOccurrence.Origin.MANUAL,
        scheduled_for=None,
        location=location if location is not None else series.default_location,
        capacity=capacity if capacity is not None else series.effective_capacity,
        notes=notes,
    )
    occurrence.full_clean()
    occurrence.save()
    return occurrence
