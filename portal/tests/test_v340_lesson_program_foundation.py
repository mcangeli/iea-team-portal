from datetime import date, datetime, time, timedelta

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.utils import timezone

from portal.model_modules.horses import Horse
from portal.model_modules.lessons import (
    LessonAssignment,
    LessonAttendanceRecord,
    LessonEnrollment,
    LessonOccurrence,
    LessonProgram,
    LessonSeries,
)
from portal.model_modules.people import OrganizationGroup, Person
from portal.models import Team


class LessonProgramFoundationTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Lesson Barn")
        self.other_team = Team.objects.create(name="Other Barn")
        self.group = OrganizationGroup.objects.create(
            team=self.team, name="Lesson Program", group_type=OrganizationGroup.GroupType.PROGRAM
        )
        self.instructor = Person.objects.create(team=self.team, first_name="Alex", last_name="Trainer")
        self.rider = Person.objects.create(team=self.team, first_name="Riley", last_name="Student")
        self.other_person = Person.objects.create(team=self.other_team, first_name="Other", last_name="Student")
        self.horse = Horse.objects.create(team=self.team, name="Comet")
        self.other_horse = Horse.objects.create(team=self.other_team, name="Nova")
        self.program = LessonProgram.objects.create(team=self.team, group=self.group, name="Core Lessons", default_capacity=6)
        self.series = LessonSeries.objects.create(
            program=self.program,
            name="Tuesday Intermediate",
            instructor=self.instructor,
            weekday=1,
            starts_at_time=time(17, 0),
            duration_minutes=60,
            default_location="Indoor Arena",
        )
        start = timezone.make_aware(datetime(2026, 9, 22, 17, 0))
        self.occurrence = LessonOccurrence.objects.create(
            series=self.series,
            title=self.series.name,
            instructor=self.series.instructor,
            starts_at=start,
            ends_at=start + timedelta(hours=1),
            location=self.series.default_location,
            capacity=self.series.effective_capacity,
        )

    def test_new_and_legacy_lesson_models_are_registered_together(self):
        self.assertIs(apps.get_model("portal", "LessonProgram"), LessonProgram)
        self.assertIsNotNone(apps.get_model("portal", "LessonGroup"))
        self.assertIsNotNone(apps.get_model("portal", "Lesson"))
        self.assertIsNotNone(apps.get_model("portal", "LessonAttendance"))
        self.assertIs(apps.get_model("portal", "LessonAttendanceRecord"), LessonAttendanceRecord)

    def test_program_requires_same_organization_program_group(self):
        wrong_group = OrganizationGroup.objects.create(
            team=self.other_team, name="Other Program", group_type=OrganizationGroup.GroupType.PROGRAM
        )
        program = LessonProgram(team=self.team, group=wrong_group, name="Invalid")
        with self.assertRaises(ValidationError):
            program.full_clean()

        team_group = OrganizationGroup.objects.create(
            team=self.team, name="Not a Program", group_type=OrganizationGroup.GroupType.TEAM
        )
        program.group = team_group
        with self.assertRaises(ValidationError):
            program.full_clean()

    def test_program_and_series_date_and_capacity_validation(self):
        program = LessonProgram(
            team=self.team, name="Bad Window", default_capacity=0,
            enrollment_opens=date(2026, 10, 1), enrollment_closes=date(2026, 9, 1),
        )
        with self.assertRaises(ValidationError):
            program.full_clean()

        series = LessonSeries(
            program=self.program, name="Bad Series", weekday=7, duration_minutes=0,
            start_date=date(2026, 10, 1), end_date=date(2026, 9, 1),
        )
        with self.assertRaises(ValidationError):
            series.full_clean()

    def test_series_effective_capacity_inherits_program_and_allows_override(self):
        self.assertEqual(self.series.effective_capacity, 6)
        self.series.capacity = 4
        self.assertEqual(self.series.effective_capacity, 4)
        self.series.capacity = None
        self.program.default_capacity = None
        self.assertIsNone(self.series.effective_capacity)

    def test_instructor_must_belong_to_program_organization(self):
        self.series.instructor = self.other_person
        with self.assertRaises(ValidationError):
            self.series.full_clean()

    def test_enrollment_is_canonical_person_and_unique_per_series(self):
        enrollment = LessonEnrollment.objects.create(series=self.series, person=self.rider)
        self.assertEqual(enrollment.person, self.rider)
        with self.assertRaises(IntegrityError), transaction.atomic():
            LessonEnrollment.objects.create(series=self.series, person=self.rider)

    def test_enrollment_status_does_not_rewrite_occurrence_history(self):
        enrollment = LessonEnrollment.objects.create(series=self.series, person=self.rider)
        LessonAttendanceRecord.objects.create(
            occurrence=self.occurrence, person=self.rider, status=LessonAttendanceRecord.Status.PRESENT
        )
        enrollment.status = LessonEnrollment.Status.WITHDRAWN
        enrollment.save()
        self.assertEqual(
            self.occurrence.attendance_records.get(person=self.rider).status,
            LessonAttendanceRecord.Status.PRESENT,
        )

    def test_enrollment_rejects_cross_organization_person_and_bad_dates(self):
        enrollment = LessonEnrollment(series=self.series, person=self.other_person)
        with self.assertRaises(ValidationError):
            enrollment.full_clean()
        enrollment.person = self.rider
        enrollment.start_date = date(2026, 10, 1)
        enrollment.end_date = date(2026, 9, 1)
        with self.assertRaises(ValidationError):
            enrollment.full_clean()

    def test_occurrence_requires_ordered_times_and_same_org_instructor(self):
        occurrence = LessonOccurrence(
            series=self.series,
            title="Invalid",
            instructor=self.other_person,
            starts_at=self.occurrence.starts_at,
            ends_at=self.occurrence.starts_at,
        )
        with self.assertRaises(ValidationError):
            occurrence.full_clean()

    def test_occurrence_is_snapshot_independent_of_series_defaults(self):
        original_title = self.occurrence.title
        original_location = self.occurrence.location
        original_capacity = self.occurrence.capacity
        self.series.name = "Renamed Series"
        self.series.default_location = "Outdoor Arena"
        self.series.capacity = 3
        self.series.save()
        self.occurrence.refresh_from_db()
        self.assertEqual(self.occurrence.title, original_title)
        self.assertEqual(self.occurrence.location, original_location)
        self.assertEqual(self.occurrence.capacity, original_capacity)

    def test_series_with_occurrence_is_protected_from_deletion(self):
        with self.assertRaises(ProtectedError):
            self.series.delete()

    def test_program_with_series_is_protected_indirectly_by_occurrence_history(self):
        with self.assertRaises(ProtectedError):
            self.program.delete()

    def test_attendance_is_unique_and_organization_scoped(self):
        LessonAttendanceRecord.objects.create(occurrence=self.occurrence, person=self.rider)
        with self.assertRaises(IntegrityError), transaction.atomic():
            LessonAttendanceRecord.objects.create(occurrence=self.occurrence, person=self.rider)
        invalid = LessonAttendanceRecord(occurrence=self.occurrence, person=self.other_person)
        with self.assertRaises(ValidationError):
            invalid.full_clean()

    def test_assignment_uses_canonical_person_and_horse_and_is_scoped(self):
        assignment = LessonAssignment.objects.create(
            occurrence=self.occurrence, person=self.rider, horse=self.horse
        )
        self.assertEqual(assignment.horse, self.horse)
        with self.assertRaises(IntegrityError), transaction.atomic():
            LessonAssignment.objects.create(
                occurrence=self.occurrence, person=self.rider, horse=self.horse
            )
        invalid = LessonAssignment(
            occurrence=self.occurrence, person=self.rider, horse=self.other_horse
        )
        with self.assertRaises(ValidationError):
            invalid.full_clean()

    def test_instructor_assignment_cannot_carry_horse(self):
        assignment = LessonAssignment(
            occurrence=self.occurrence,
            person=self.instructor,
            role=LessonAssignment.Role.INSTRUCTOR,
            horse=self.horse,
        )
        with self.assertRaises(ValidationError):
            assignment.full_clean()

    def test_person_and_horse_history_references_are_protected(self):
        LessonAttendanceRecord.objects.create(occurrence=self.occurrence, person=self.rider)
        LessonAssignment.objects.create(occurrence=self.occurrence, person=self.rider, horse=self.horse)
        with self.assertRaises(ProtectedError):
            self.rider.delete()
        with self.assertRaises(ProtectedError):
            self.horse.delete()
