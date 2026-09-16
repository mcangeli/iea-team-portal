from datetime import datetime, time, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from portal.model_modules.horses import Horse
from portal.model_modules.lessons import LessonAssignment, LessonAttendanceRecord, LessonEnrollment, LessonOccurrence, LessonParticipantMove, LessonProgram, LessonSeries
from portal.model_modules.people import Person
from portal.models import Team
from portal.services.lesson_participant_moves import destination_accepts_participant, move_lesson_participant
from portal.services.lesson_preparation import prepare_lesson_occurrence


class LessonParticipantMoveTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Move Barn")
        self.person = Person.objects.create(team=self.team, first_name="Riley", last_name="Rider")
        self.program = LessonProgram.objects.create(team=self.team, name="Barn Lessons")
        self.series = LessonSeries.objects.create(program=self.program, name="Tuesday", weekday=1, starts_at_time=time(17), duration_minutes=60)
        LessonEnrollment.objects.create(series=self.series, person=self.person)
        start = timezone.make_aware(datetime(2026, 9, 22, 17))
        self.source = LessonOccurrence.objects.create(series=self.series, title="Tuesday", starts_at=start, ends_at=start + timedelta(hours=1))
        self.destination = LessonOccurrence.objects.create(series=self.series, title="Tuesday", starts_at=start + timedelta(days=7), ends_at=start + timedelta(days=7, hours=1))
        prepare_lesson_occurrence(self.source)

    def test_makeup_preserves_source_and_materializes_destination(self):
        result = move_lesson_participant(source_occurrence=self.source, destination_occurrence=self.destination, person=self.person, reason="School event")
        self.assertEqual(result.source_attendance.status, LessonAttendanceRecord.Status.EXCUSED)
        self.assertEqual(result.destination_attendance.status, LessonAttendanceRecord.Status.MAKEUP)
        self.assertEqual(result.destination_assignment.role, LessonAssignment.Role.PARTICIPANT)
        self.assertEqual(LessonParticipantMove.objects.count(), 1)

    def test_prepared_expected_destination_is_reused_for_makeup(self):
        prepare_lesson_occurrence(self.destination)
        expected = LessonAttendanceRecord.objects.get(occurrence=self.destination, person=self.person)
        self.assertEqual(expected.status, LessonAttendanceRecord.Status.EXPECTED)
        self.assertTrue(destination_accepts_participant(self.destination, self.person))
        result = move_lesson_participant(source_occurrence=self.source, destination_occurrence=self.destination, person=self.person)
        self.assertEqual(result.destination_attendance.pk, expected.pk)
        self.assertEqual(result.destination_attendance.status, LessonAttendanceRecord.Status.MAKEUP)

    def test_regular_move_uses_expected_destination_status(self):
        result = move_lesson_participant(source_occurrence=self.source, destination_occurrence=self.destination, person=self.person, kind=LessonParticipantMove.Kind.MOVE)
        self.assertEqual(result.destination_attendance.status, LessonAttendanceRecord.Status.EXPECTED)

    def test_carry_horse_is_explicit(self):
        horse = Horse.objects.create(team=self.team, name="Scout")
        assignment = LessonAssignment.objects.get(occurrence=self.source, person=self.person, role=LessonAssignment.Role.PARTICIPANT)
        assignment.horse = horse; assignment.save()
        result = move_lesson_participant(source_occurrence=self.source, destination_occurrence=self.destination, person=self.person, carry_horse=True)
        self.assertEqual(result.destination_assignment.horse, horse)

    def test_horse_is_not_carried_by_default(self):
        horse = Horse.objects.create(team=self.team, name="Scout")
        assignment = LessonAssignment.objects.get(occurrence=self.source, person=self.person, role=LessonAssignment.Role.PARTICIPANT)
        assignment.horse = horse; assignment.save()
        result = move_lesson_participant(source_occurrence=self.source, destination_occurrence=self.destination, person=self.person)
        self.assertIsNone(result.destination_assignment.horse)

    def test_second_move_from_same_source_is_rejected_even_to_different_destination(self):
        move_lesson_participant(source_occurrence=self.source, destination_occurrence=self.destination, person=self.person)
        later = LessonOccurrence.objects.create(series=self.series, title="Tuesday", starts_at=self.destination.starts_at + timedelta(days=7), ends_at=self.destination.ends_at + timedelta(days=7))
        with self.assertRaises(ValidationError):
            move_lesson_participant(source_occurrence=self.source, destination_occurrence=later, person=self.person)

    def test_duplicate_destination_move_is_rejected(self):
        move_lesson_participant(source_occurrence=self.source, destination_occurrence=self.destination, person=self.person)
        with self.assertRaises(ValidationError):
            move_lesson_participant(source_occurrence=self.source, destination_occurrence=self.destination, person=self.person)

    def test_existing_attendance_history_blocks_destination(self):
        prepare_lesson_occurrence(self.destination)
        attendance = LessonAttendanceRecord.objects.get(occurrence=self.destination, person=self.person)
        attendance.status = LessonAttendanceRecord.Status.PRESENT
        attendance.save()
        self.assertFalse(destination_accepts_participant(self.destination, self.person))
        with self.assertRaises(ValidationError):
            move_lesson_participant(source_occurrence=self.source, destination_occurrence=self.destination, person=self.person)

    def test_cross_organization_destination_is_rejected(self):
        other = Team.objects.create(name="Other Barn")
        other_program = LessonProgram.objects.create(team=other, name="Other")
        other_series = LessonSeries.objects.create(program=other_program, name="Other")
        other_start = self.destination.starts_at + timedelta(days=1)
        other_occurrence = LessonOccurrence.objects.create(series=other_series, title="Other", starts_at=other_start)
        with self.assertRaises(ValidationError):
            move_lesson_participant(source_occurrence=self.source, destination_occurrence=other_occurrence, person=self.person)

    def test_completed_destination_is_rejected(self):
        self.destination.status = LessonOccurrence.Status.COMPLETED; self.destination.save()
        with self.assertRaises(ValidationError):
            move_lesson_participant(source_occurrence=self.source, destination_occurrence=self.destination, person=self.person)

    def test_earlier_destination_is_rejected(self):
        earlier = LessonOccurrence.objects.create(series=self.series, title="Earlier", starts_at=self.source.starts_at - timedelta(days=7))
        with self.assertRaises(ValidationError):
            move_lesson_participant(source_occurrence=self.source, destination_occurrence=earlier, person=self.person)
