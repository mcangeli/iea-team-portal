from datetime import date, datetime, time, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from portal.model_modules.lessons import (
    LessonAssignment,
    LessonAttendanceRecord,
    LessonOccurrence,
    LessonProgram,
    LessonSeries,
)
from portal.model_modules.people import Person
from portal.models import Team
from portal.services.lesson_scheduling import (
    cancel_lesson_occurrence,
    create_manual_lesson_occurrence,
    generate_lesson_occurrences,
    refresh_future_lesson_occurrences,
    reschedule_lesson_occurrence,
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

    def test_future_refresh_updates_only_uncommitted_scheduled_occurrences(self):
        result = generate_lesson_occurrences(self.series, date(2026, 9, 22), date(2026, 10, 6))
        self.series.name = "Tuesday Advanced"
        self.series.default_location = "Outdoor Arena"
        self.series.duration_minutes = 75
        self.series.capacity = 4
        self.series.save()
        cutoff = timezone.make_aware(datetime(2026, 9, 20, 0, 0))
        refreshed = refresh_future_lesson_occurrences(self.series, from_datetime=cutoff)
        self.assertEqual(len(refreshed.updated), 3)
        self.assertEqual(len(refreshed.preserved), 0)
        for occurrence in result.created:
            occurrence.refresh_from_db()
            self.assertEqual(occurrence.title, "Tuesday Advanced")
            self.assertEqual(occurrence.location, "Outdoor Arena")
            self.assertEqual(occurrence.capacity, 4)
            self.assertEqual(occurrence.ends_at - occurrence.starts_at, timedelta(minutes=75))

    def test_future_refresh_preserves_cancelled_and_rescheduled_occurrences(self):
        occurrences = generate_lesson_occurrences(self.series, date(2026, 9, 22), date(2026, 9, 29)).created
        cancelled, rescheduled = occurrences
        cancel_lesson_occurrence(cancelled, notes="Weather")
        new_start = rescheduled.starts_at + timedelta(days=1)
        reschedule_lesson_occurrence(rescheduled, starts_at=new_start, notes="Arena conflict")
        self.series.default_location = "New Arena"
        self.series.save()
        cutoff = timezone.make_aware(datetime(2026, 9, 20, 0, 0))
        refreshed = refresh_future_lesson_occurrences(self.series, from_datetime=cutoff)
        self.assertEqual(len(refreshed.updated), 0)
        self.assertEqual(len(refreshed.preserved), 2)
        cancelled.refresh_from_db()
        rescheduled.refresh_from_db()
        self.assertEqual(cancelled.status, LessonOccurrence.Status.CANCELLED)
        self.assertEqual(cancelled.notes, "Weather")
        self.assertEqual(rescheduled.status, LessonOccurrence.Status.RESCHEDULED)
        self.assertEqual(rescheduled.starts_at, new_start)

    def test_future_refresh_preserves_occurrence_with_attendance(self):
        occurrence = generate_lesson_occurrences(self.series, date(2026, 9, 22), date(2026, 9, 22)).created[0]
        rider = Person.objects.create(team=self.team, first_name="Riley", last_name="Student")
        LessonAttendanceRecord.objects.create(occurrence=occurrence, person=rider)
        self.series.default_location = "New Arena"
        self.series.save()
        refreshed = refresh_future_lesson_occurrences(
            self.series, from_datetime=timezone.make_aware(datetime(2026, 9, 20, 0, 0))
        )
        self.assertEqual(len(refreshed.updated), 0)
        self.assertEqual(len(refreshed.preserved), 1)
        occurrence.refresh_from_db()
        self.assertEqual(occurrence.location, "Indoor Arena")

    def test_future_refresh_preserves_occurrence_with_assignment(self):
        occurrence = generate_lesson_occurrences(self.series, date(2026, 9, 22), date(2026, 9, 22)).created[0]
        LessonAssignment.objects.create(
            occurrence=occurrence,
            person=self.instructor,
            role=LessonAssignment.Role.INSTRUCTOR,
        )
        self.series.default_location = "New Arena"
        self.series.save()
        refreshed = refresh_future_lesson_occurrences(
            self.series, from_datetime=timezone.make_aware(datetime(2026, 9, 20, 0, 0))
        )
        self.assertEqual(len(refreshed.updated), 0)
        self.assertEqual(len(refreshed.preserved), 1)

    def test_refresh_does_not_move_occurrence_when_series_schedule_shape_changes(self):
        occurrence = generate_lesson_occurrences(self.series, date(2026, 9, 22), date(2026, 9, 22)).created[0]
        original_start = occurrence.starts_at
        self.series.weekday = 2
        self.series.starts_at_time = time(18, 0)
        self.series.save()
        refresh_future_lesson_occurrences(
            self.series, from_datetime=timezone.make_aware(datetime(2026, 9, 20, 0, 0))
        )
        occurrence.refresh_from_db()
        self.assertEqual(occurrence.starts_at, original_start)

    def test_cancel_rejects_completed_occurrence(self):
        occurrence = generate_lesson_occurrences(self.series, date(2026, 9, 22), date(2026, 9, 22)).created[0]
        occurrence.status = LessonOccurrence.Status.COMPLETED
        occurrence.save()
        with self.assertRaises(ValidationError):
            cancel_lesson_occurrence(occurrence)

    def test_reschedule_preserves_duration_and_snapshot_fields(self):
        occurrence = generate_lesson_occurrences(self.series, date(2026, 9, 22), date(2026, 9, 22)).created[0]
        old_title = occurrence.title
        old_location = occurrence.location
        old_capacity = occurrence.capacity
        new_start = occurrence.starts_at + timedelta(days=2, hours=1)
        reschedule_lesson_occurrence(occurrence, starts_at=new_start)
        occurrence.refresh_from_db()
        self.assertEqual(occurrence.status, LessonOccurrence.Status.RESCHEDULED)
        self.assertEqual(occurrence.starts_at, new_start)
        self.assertEqual(occurrence.ends_at, new_start + timedelta(minutes=60))
        self.assertEqual(occurrence.title, old_title)
        self.assertEqual(occurrence.location, old_location)
        self.assertEqual(occurrence.capacity, old_capacity)

    def test_reschedule_rejects_completed_occurrence(self):
        occurrence = generate_lesson_occurrences(self.series, date(2026, 9, 22), date(2026, 9, 22)).created[0]
        occurrence.status = LessonOccurrence.Status.COMPLETED
        occurrence.save()
        with self.assertRaises(ValidationError):
            reschedule_lesson_occurrence(occurrence, starts_at=occurrence.starts_at + timedelta(days=1))
