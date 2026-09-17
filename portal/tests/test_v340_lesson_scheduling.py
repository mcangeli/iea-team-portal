from datetime import date, datetime, time, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from portal.model_modules.lessons import LessonAssignment, LessonAttendanceRecord, LessonOccurrence, LessonProgram, LessonSeries
from portal.model_modules.people import OrganizationRoleAssignment, Person
from portal.models import Team
from portal.services.lesson_scheduling import cancel_lesson_occurrence, create_manual_lesson_occurrence, generate_lesson_occurrences, refresh_future_lesson_occurrences, reschedule_lesson_occurrence


class LessonSchedulingTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Scheduling Barn")
        self.instructor = Person.objects.create(team=self.team, first_name="Alex", last_name="Trainer")
        OrganizationRoleAssignment.objects.create(team=self.team, person=self.instructor, role=OrganizationRoleAssignment.Role.TRAINER)
        self.program = LessonProgram.objects.create(team=self.team, name="Lesson Program", default_capacity=6)
        self.series = LessonSeries.objects.create(program=self.program, name="Tuesday Intermediate", instructor=self.instructor, weekday=1, starts_at_time=time(17, 0), duration_minutes=60, default_location="Indoor Arena", start_date=date(2026, 9, 1), end_date=date(2026, 10, 31))

    def _refresh_cutoff(self):
        return timezone.make_aware(datetime(2026, 9, 1, 0, 0), timezone.get_current_timezone())

    def test_generation_materializes_only_matching_weekdays(self):
        result = generate_lesson_occurrences(self.series, date(2026, 9, 1), date(2026, 9, 30))
        self.assertEqual(len(result.created), 5)
        self.assertEqual([item.starts_at.date() for item in result.created], [date(2026, 9, 1), date(2026, 9, 8), date(2026, 9, 15), date(2026, 9, 22), date(2026, 9, 29)])

    def test_generation_respects_series_date_boundaries(self):
        result = generate_lesson_occurrences(self.series, date(2026, 8, 1), date(2026, 12, 31))
        self.assertTrue(result.created)
        self.assertGreaterEqual(result.created[0].starts_at.date(), self.series.start_date)
        self.assertLessEqual(result.created[-1].starts_at.date(), self.series.end_date)

    def test_generation_snapshots_series_defaults_and_identity(self):
        occurrence = generate_lesson_occurrences(self.series, date(2026, 9, 1), date(2026, 9, 1)).created[0]
        self.assertEqual(occurrence.title, self.series.name)
        self.assertEqual(occurrence.instructor, self.instructor)
        self.assertEqual(occurrence.location, "Indoor Arena")
        self.assertEqual(occurrence.capacity, 6)
        self.assertEqual(occurrence.ends_at - occurrence.starts_at, timedelta(minutes=60))
        self.assertEqual(occurrence.origin, LessonOccurrence.Origin.GENERATED)
        self.assertEqual(occurrence.scheduled_for, occurrence.starts_at)

    def test_generation_is_idempotent(self):
        first = generate_lesson_occurrences(self.series, date(2026, 9, 1), date(2026, 9, 15))
        second = generate_lesson_occurrences(self.series, date(2026, 9, 1), date(2026, 9, 15))
        self.assertEqual(len(first.created), 3)
        self.assertEqual(len(second.created), 0)
        self.assertEqual(len(second.existing), 3)
        self.assertEqual(LessonOccurrence.objects.count(), 3)

    def test_generation_does_not_rewrite_existing_occurrence(self):
        occurrence = generate_lesson_occurrences(self.series, date(2026, 9, 1), date(2026, 9, 1)).created[0]
        occurrence.title = "Staff-edited title"; occurrence.location = "Outdoor Arena"; occurrence.save(update_fields=["title", "location"])
        self.series.name = "Renamed Series"; self.series.default_location = "New Default"; self.series.save(update_fields=["name", "default_location"])
        result = generate_lesson_occurrences(self.series, date(2026, 9, 1), date(2026, 9, 1))
        occurrence.refresh_from_db()
        self.assertEqual(len(result.created), 0); self.assertEqual(occurrence.title, "Staff-edited title"); self.assertEqual(occurrence.location, "Outdoor Arena")

    def test_inactive_series_is_rejected(self):
        self.series.active = False; self.series.save(update_fields=["active"])
        with self.assertRaises(ValidationError): generate_lesson_occurrences(self.series, date(2026, 9, 1), date(2026, 9, 30))

    def test_incomplete_schedule_is_rejected(self):
        self.series.weekday = None; self.series.save(update_fields=["weekday"])
        with self.assertRaises(ValidationError): generate_lesson_occurrences(self.series, date(2026, 9, 1), date(2026, 9, 30))

    def test_unsaved_series_is_rejected(self):
        series = LessonSeries(program=self.program, name="Unsaved", weekday=1, starts_at_time=time(17), duration_minutes=60)
        with self.assertRaises(ValidationError): generate_lesson_occurrences(series, date(2026, 9, 1), date(2026, 9, 30))

    def test_generated_datetimes_are_timezone_aware(self):
        occurrence = generate_lesson_occurrences(self.series, date(2026, 9, 1), date(2026, 9, 1)).created[0]
        self.assertTrue(timezone.is_aware(occurrence.starts_at)); self.assertTrue(timezone.is_aware(occurrence.ends_at))

    def test_manual_occurrence_has_no_recurrence_identity(self):
        starts_at = timezone.make_aware(datetime(2026, 9, 3, 18, 0))
        occurrence = create_manual_lesson_occurrence(self.series, starts_at=starts_at, title="Makeup Lesson", location="Outdoor Arena")
        self.assertEqual(occurrence.origin, LessonOccurrence.Origin.MANUAL); self.assertIsNone(occurrence.scheduled_for)

    def test_manual_occurrence_uses_series_duration_when_end_omitted(self):
        starts_at = timezone.make_aware(datetime(2026, 9, 3, 18, 0))
        occurrence = create_manual_lesson_occurrence(self.series, starts_at=starts_at)
        self.assertEqual(occurrence.ends_at - occurrence.starts_at, timedelta(minutes=60))

    def test_future_refresh_updates_only_uncommitted_scheduled_occurrences(self):
        result = generate_lesson_occurrences(self.series, date(2026, 9, 22), date(2026, 10, 6))
        first, second, third = result.created
        first.status = LessonOccurrence.Status.COMPLETED; first.save(update_fields=["status"])
        self.series.default_location = "Outdoor Arena"; self.series.capacity = 8; self.series.save(update_fields=["default_location", "capacity"])
        refreshed = refresh_future_lesson_occurrences(self.series, from_datetime=self._refresh_cutoff())
        first.refresh_from_db(); second.refresh_from_db(); third.refresh_from_db()
        self.assertEqual(first.location, "Indoor Arena"); self.assertEqual(second.location, "Outdoor Arena"); self.assertEqual(third.capacity, 8); self.assertEqual(len(refreshed.updated), 2); self.assertEqual(len(refreshed.preserved), 1)

    def test_future_refresh_preserves_cancelled_and_rescheduled_occurrences(self):
        cancelled, rescheduled = generate_lesson_occurrences(self.series, date(2026, 9, 22), date(2026, 9, 29)).created
        cancelled.status = LessonOccurrence.Status.CANCELLED; cancelled.save(update_fields=["status"])
        rescheduled.status = LessonOccurrence.Status.RESCHEDULED; rescheduled.save(update_fields=["status"])
        refreshed = refresh_future_lesson_occurrences(self.series, from_datetime=self._refresh_cutoff())
        self.assertEqual(len(refreshed.updated), 0); self.assertEqual(len(refreshed.preserved), 2)

    def test_future_refresh_preserves_occurrence_with_attendance(self):
        occurrence = generate_lesson_occurrences(self.series, date(2026, 9, 22), date(2026, 9, 22)).created[0]
        rider = Person.objects.create(team=self.team, first_name="Riley", last_name="Student")
        LessonAttendanceRecord.objects.create(occurrence=occurrence, person=rider)
        self.series.default_location = "Changed"; self.series.save(update_fields=["default_location"])
        refreshed = refresh_future_lesson_occurrences(self.series, from_datetime=self._refresh_cutoff())
        occurrence.refresh_from_db(); self.assertEqual(occurrence.location, "Indoor Arena"); self.assertEqual(len(refreshed.preserved), 1)

    def test_future_refresh_preserves_occurrence_with_assignment(self):
        occurrence = generate_lesson_occurrences(self.series, date(2026, 9, 22), date(2026, 9, 22)).created[0]
        rider = Person.objects.create(team=self.team, first_name="Riley", last_name="Student")
        LessonAssignment.objects.create(occurrence=occurrence, person=rider)
        refreshed = refresh_future_lesson_occurrences(self.series, from_datetime=self._refresh_cutoff())
        self.assertEqual(len(refreshed.preserved), 1)

    def test_refresh_does_not_move_occurrence_when_series_schedule_shape_changes(self):
        occurrence = generate_lesson_occurrences(self.series, date(2026, 9, 22), date(2026, 9, 22)).created[0]
        original_start = occurrence.starts_at; original_slot = occurrence.scheduled_for
        self.series.weekday = 3; self.series.starts_at_time = time(19); self.series.save(update_fields=["weekday", "starts_at_time"])
        refresh_future_lesson_occurrences(self.series, from_datetime=self._refresh_cutoff())
        occurrence.refresh_from_db(); self.assertEqual(occurrence.starts_at, original_start); self.assertEqual(occurrence.scheduled_for, original_slot)

    def test_cancel_rejects_completed_occurrence(self):
        occurrence = generate_lesson_occurrences(self.series, date(2026, 9, 22), date(2026, 9, 22)).created[0]
        occurrence.status = LessonOccurrence.Status.COMPLETED; occurrence.save(update_fields=["status"])
        with self.assertRaises(ValidationError): cancel_lesson_occurrence(occurrence)

    def test_reschedule_preserves_duration_snapshot_and_recurrence_identity(self):
        occurrence = generate_lesson_occurrences(self.series, date(2026, 9, 22), date(2026, 9, 22)).created[0]
        original_slot = occurrence.scheduled_for
        new_start = occurrence.starts_at + timedelta(days=1, hours=1)
        result = reschedule_lesson_occurrence(occurrence, starts_at=new_start)
        self.assertEqual(result.starts_at, new_start); self.assertEqual(result.ends_at - result.starts_at, timedelta(minutes=60)); self.assertEqual(result.status, LessonOccurrence.Status.RESCHEDULED); self.assertEqual(result.scheduled_for, original_slot)

    def test_generation_after_reschedule_does_not_recreate_original_slot(self):
        occurrence = generate_lesson_occurrences(self.series, date(2026, 9, 22), date(2026, 9, 22)).created[0]
        original_slot = occurrence.scheduled_for
        reschedule_lesson_occurrence(occurrence, starts_at=occurrence.starts_at + timedelta(days=1))
        result = generate_lesson_occurrences(self.series, date(2026, 9, 22), date(2026, 9, 22))
        self.assertEqual(len(result.created), 0); self.assertEqual(len(result.existing), 1); self.assertEqual(result.existing[0].scheduled_for, original_slot)

    def test_manual_occurrence_same_time_as_generated_is_distinct(self):
        generated = generate_lesson_occurrences(self.series, date(2026, 9, 22), date(2026, 9, 22)).created[0]
        manual = create_manual_lesson_occurrence(self.series, starts_at=generated.starts_at, title="Extra Session")
        self.assertNotEqual(generated.pk, manual.pk); self.assertIsNone(manual.scheduled_for)

    def test_reschedule_rejects_completed_occurrence(self):
        occurrence = generate_lesson_occurrences(self.series, date(2026, 9, 22), date(2026, 9, 22)).created[0]
        occurrence.status = LessonOccurrence.Status.COMPLETED; occurrence.save(update_fields=["status"])
        with self.assertRaises(ValidationError): reschedule_lesson_occurrence(occurrence, starts_at=occurrence.starts_at + timedelta(days=1))
