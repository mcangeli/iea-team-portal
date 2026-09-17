from dataclasses import dataclass
from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction

from portal.model_modules.lessons import LessonOccurrence, LessonSeries
from portal.services.lesson_preparation import (
    LessonOccurrencePreparationResult,
    prepare_lesson_occurrence,
)
from portal.services.lesson_scheduling import (
    LessonOccurrenceGenerationResult,
    generate_lesson_occurrences,
)


@dataclass(frozen=True)
class PreparedLessonOccurrence:
    occurrence: LessonOccurrence
    preparation: LessonOccurrencePreparationResult


@dataclass(frozen=True)
class LessonSeriesMaterializationResult:
    generation: LessonOccurrenceGenerationResult
    prepared: tuple[PreparedLessonOccurrence, ...]
    skipped: tuple[LessonOccurrence, ...]


def materialize_lesson_series(
    series: LessonSeries,
    start_date: date,
    end_date: date,
    *,
    prepare_existing: bool = True,
) -> LessonSeriesMaterializationResult:
    """Generate a series window and prepare eligible scheduled occurrences atomically.

    Newly generated occurrences are always prepared. Existing occurrences are also
    prepared by default when they remain SCHEDULED; operational statuses are skipped.
    Existing attendance/assignments remain authoritative because preparation itself
    is additive and idempotent.
    """
    if not series.pk:
        raise ValidationError("Lesson series must be saved before materialization.")

    prepared = []
    skipped = []

    with transaction.atomic():
        generation = generate_lesson_occurrences(series, start_date, end_date)
        candidates = list(generation.created)
        if prepare_existing:
            candidates.extend(generation.existing)

        seen_ids = set()
        for occurrence in candidates:
            if occurrence.pk in seen_ids:
                continue
            seen_ids.add(occurrence.pk)
            if occurrence.status != LessonOccurrence.Status.SCHEDULED:
                skipped.append(occurrence)
                continue
            preparation = prepare_lesson_occurrence(occurrence)
            prepared.append(PreparedLessonOccurrence(occurrence, preparation))

    return LessonSeriesMaterializationResult(
        generation=generation,
        prepared=tuple(prepared),
        skipped=tuple(skipped),
    )
