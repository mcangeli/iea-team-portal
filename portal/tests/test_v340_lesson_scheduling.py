from datetime import date, datetime, time, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from portal.model_modules.lessons import LessonOccurrence, LessonProgram, LessonSeries
from portal.model_modules.people import Person
from portal.models import Team
from portal.services.lesson_scheduling import (
    create_manual_lesson_occurrence,
    generate_lesson_occurrences,
)


class LessonSchedulingTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Scheduling Barn")
        self.instructor = Person.objects.create(team=self.team, first_name="Alex", last_name="Trainer")
        self.program = LessonProgram.objects.create(team=self.team, name="Lesson Program", default_capacity=6)
        self.series = LessonSeries.objects.create(
            program=self.program,
            name="Tuesday Intermediate",
            instructor=self.instructor,
            weekday=1,
            starts_at_time=time(17, 0),
            duration_minutes=60,
            default_location="Indoor Arena",
            start_date=date(2026, 9, 1),
            end_date=date(2026, 10, 31),
        )

    def test_generation_materializes_only_matching_weekdays(self):
        result = generate_lesson_occurrences(self.series, date(2026, 9, 1), date(2026, 9, 30))
        self.assertEqual(len(result.created), 5)
        self.assertEqual(len(result.existing), 0)
        self.assertEqual([item.starts_at.date() for item in result.created], [
            date(2026, 9, 1), date(2026, 9, 8), date(2026, 9, 15), date(2026, 9, 22), date(2026, 9, 29)
        ])

    def test_generation_respects_series_date_boundaries(self):
        result = generate_lesson_occurrences(self.series, date(2026, 8, 1), date(2026, 12, 31))
        self.assertTrue(result.created)
        self.assertGreaterEqual(result.created[0].starts_at.date(), self.series.start_date)
        self.assertLessEqual(result.created[-1].starts_at.date(), self.series.end_date)

    def test_generation_snapshots_series_defaults(self):
        occurrence = generate_lesson_occurrences(self.series, date(2026, 9, 1), date(2026, 9, 1)).created[0]
        self.assertEqual(occurrence.title, self.series.name)
        self.assertEqual(occurrence.instructor, self.instructor)
        self.assertEqual(occurrence.location, "Indoor Arena")
        self.assertEqual(occurrence.capacity, 6)
        self.assertEqual(occurrence.ends_at - occurrence.starts_at, timedelta(minutes=60))

    def test_generation_is_idempotent(self):
        first = generate_lesson_occurrences(self.series, date(2026, 9, 1), date(2026, 9, 15))
        second = generate_lesson_occurrences(self.series, date(2026, 9, 1), date(2026, 9, 15))
        self.assertEqual(len(first.created), 3)
        self.assertEqual(len(second.created), 0)
        self.assertEqual(len(second.existing), 3)
        self.assertEqual(LessonOccurrence.objects.count(), 3)

    def test_generation_does_not_rewrite_existing_occurrence(self):
        occurrence = generate_lesson_occurrences(self.series, date(2026, 9, 1), date(2026, 9, 1)).created[0]
        occurrence.status = LessonOccurrence.Status.CANCELLED
        occurrence.location = "Weather cancellation"
        occurrence.save()
        self.series.default_location = "Outdoor Arena"
        self.series.save()
        result = generate_lesson_occurrences(self.series, date(2026, 9, 1), date(2026, 9, 1))
        occurrence.refresh_from_db()
        self.assertEqual(len(result.created), 0)
        self.assertEqual(occurrence.status, LessonOccurrence.Status.CANCELLED)
        self.assertEqual(occurrence.location, "Weather cancellation")

    def test_generation_requires_complete_active_schedule(self):
        self.series.active = False
        with self.assertRaises(ValidationError):
            generate_lesson_occurrences(self.series, date(2026, 9, 1), date(2026, 9, 30))
        self.series.active = True
        self.series.weekday = None
        with self.assertRaises(ValidationError):
            generate_lesson_occurrences(self.series, date(2026, 9, 1), date(2026, 9, 30))

    def test_generation_rejects_reversed_request_window(self):
        with self.assertRaises(ValidationError):
            generate_lesson_occurrences(self.series, date(2026, 10, 1), date(2026, 9, 1))

    def test_generated_datetimes_are_timezone_aware(self):
        occurrence = generate_lesson_occurrences(self.series, date(2026, 9, 1), date(2026, 9, 1)).created[0]
        self.assertTrue(timezone.is_aware(occurrence.starts_at))
        self.assertTrue(timezone.is_aware(occurrence.ends_at))

    def test_manual_occurrence_does_not_change_recurring_schedule(self):
        starts_at = timezone.make_aware(datetime(2026, 9, 3, 18, 30))
        occurrence = create_manual_lesson_occurrence(
            self.series,
            starts_at=starts_at,
            title="Makeup Lesson",
            location="Outdoor Arena",
        )
        self.assertEqual(occurrence.starts_at, starts_at)
        self.assertEqual(occurrence.title, "Makeup Lesson")
        self.assertEqual(occurrence.location, "Outdoor Arena")
        self.assertEqual(self.series.weekday, 1)
        self.assertEqual(self.series.starts_at_time, time(17, 0))

    def test_manual_occurrence_uses_series_duration_when_end_omitted(self):
        starts_at = timezone.make_aware(datetime(2026, 9, 3, 18, 30))
        occurrence = create_manual_lesson_occurrence(self.series, starts_at=starts_at)
        self.assertEqual(occurrence.ends_at, starts_at + timedelta(minutes=60))
