from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from portal.model_modules.horses import Horse
from portal.model_modules.lessons import (
    IEALessonSeriesContext,
    LessonAssignment,
    LessonAttendanceRecord,
    LessonOccurrence,
    LessonProgram,
)
from portal.model_modules.people import LegacyPersonLink, Person
from portal.models import Lesson, LessonAttendance, LessonGroup, Rider, Season, SeasonMembership, Team
from portal.services.legacy_iea_lessons import convert_legacy_iea_lessons


class LegacyIEALessonConversionTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Conversion Barn")
        self.season = Season.objects.create(
            team=self.team,
            name="2026-2027",
            start_date=datetime(2026, 8, 1).date(),
            end_date=datetime(2027, 5, 31).date(),
            is_active=True,
        )
        self.coach_user = User.objects.create_user("coach", password="test")
        self.coach_person = Person.objects.create(team=self.team, user=self.coach_user, first_name="Casey", last_name="Coach")
        self.group = LessonGroup.objects.create(
            season=self.season,
            name="Upper Tuesday",
            team_level=LessonGroup.TeamLevel.UPPER,
            coach=self.coach_user,
            default_location="Main Ring",
        )
        self.rider = Rider.objects.create(team=self.team, first_name="Alex", last_name="Rider", grade=10)
        self.person = Person.objects.create(team=self.team, first_name="Alex", last_name="Rider")
        LegacyPersonLink.objects.create(person=self.person, rider=self.rider)
        SeasonMembership.objects.create(rider=self.rider, season=self.season, team_level=SeasonMembership.TeamLevel.UPPER)
        self.group.riders.add(self.rider)
        self.starts_at = timezone.make_aware(datetime(2026, 9, 15, 17, 0))
        self.lesson = Lesson.objects.create(
            team=self.team,
            season=self.season,
            group=self.group,
            coach=self.coach_user,
            title="Upper Team Lesson",
            starts_at=self.starts_at,
            ends_at=self.starts_at + timedelta(hours=1),
            location="Outdoor Ring",
            notes="Legacy lesson note",
        )
        self.legacy_attendance = LessonAttendance.objects.create(
            lesson=self.lesson,
            rider=self.rider,
            status=LessonAttendance.Status.PRESENT,
            notes="Worked without stirrups",
        )

    def _add_futures_rider(self, *, with_person=True, with_attendance=True):
        rider = Rider.objects.create(team=self.team, first_name="Fin", last_name="Future", grade=7)
        person = None
        if with_person:
            person = Person.objects.create(team=self.team, first_name="Fin", last_name="Future")
            LegacyPersonLink.objects.create(person=person, rider=rider)
        SeasonMembership.objects.create(rider=rider, season=self.season, team_level=SeasonMembership.TeamLevel.FUTURES)
        self.group.riders.add(rider)
        attendance = None
        if with_attendance:
            attendance = LessonAttendance.objects.create(lesson=self.lesson, rider=rider, status=LessonAttendance.Status.EXCUSED)
        return rider, person, attendance

    def test_dry_run_reports_without_writing(self):
        report = convert_legacy_iea_lessons(season=self.season, dry_run=True)
        self.assertEqual(report.lessons_scanned, 1)
        self.assertEqual(report.lessons_convertible, 1)
        self.assertEqual(report.issue_count, 0)
        self.assertEqual(LessonProgram.objects.count(), 0)
        self.assertEqual(LessonOccurrence.objects.count(), 0)

    def test_apply_creates_iea_series_and_occurrence(self):
        report = convert_legacy_iea_lessons(season=self.season, dry_run=False)
        self.assertEqual(report.occurrences_created, 1)
        occurrence = LessonOccurrence.objects.select_related("series", "series__iea_context").get()
        self.assertEqual(occurrence.title, self.lesson.title)
        self.assertEqual(occurrence.starts_at, self.lesson.starts_at)
        self.assertEqual(occurrence.ends_at, self.lesson.ends_at)
        self.assertEqual(occurrence.location, self.lesson.location)
        self.assertEqual(occurrence.notes, self.lesson.notes)
        self.assertEqual(occurrence.instructor, self.coach_person)
        self.assertEqual(occurrence.series.iea_context.season, self.season)
        self.assertEqual(occurrence.series.iea_context.team_level, IEALessonSeriesContext.TeamLevel.UPPER)

    def test_apply_preserves_attendance_and_canonical_horse_assignment(self):
        horse = Horse.objects.create(team=self.team, name="Scout")
        self.legacy_attendance.horse_name = "scout"
        self.legacy_attendance.save(update_fields=["horse_name"])
        convert_legacy_iea_lessons(season=self.season, dry_run=False)
        attendance = LessonAttendanceRecord.objects.get()
        assignment = LessonAssignment.objects.get()
        self.assertEqual(attendance.person, self.person)
        self.assertEqual(attendance.status, LessonAttendanceRecord.Status.PRESENT)
        self.assertEqual(attendance.notes, "Worked without stirrups")
        self.assertEqual(assignment.person, self.person)
        self.assertEqual(assignment.horse, horse)

    def test_unknown_legacy_horse_name_is_preserved_in_assignment_notes(self):
        self.legacy_attendance.horse_name = "Old School Horse"
        self.legacy_attendance.save(update_fields=["horse_name"])
        convert_legacy_iea_lessons(season=self.season, dry_run=False)
        assignment = LessonAssignment.objects.get()
        self.assertIsNone(assignment.horse)
        self.assertEqual(assignment.notes, "Legacy horse: Old School Horse")

    def test_cancelled_lesson_becomes_cancelled_occurrence(self):
        self.lesson.cancelled = True
        self.lesson.save(update_fields=["cancelled"])
        convert_legacy_iea_lessons(season=self.season, dry_run=False)
        self.assertEqual(LessonOccurrence.objects.get().status, LessonOccurrence.Status.CANCELLED)

    def test_repeated_apply_is_idempotent_and_does_not_overwrite_operations(self):
        convert_legacy_iea_lessons(season=self.season, dry_run=False)
        attendance = LessonAttendanceRecord.objects.get()
        attendance.status = LessonAttendanceRecord.Status.EXCUSED
        attendance.save(update_fields=["status"])
        assignment = LessonAssignment.objects.get()
        assignment.notes = "Operational note"
        assignment.save(update_fields=["notes"])

        report = convert_legacy_iea_lessons(season=self.season, dry_run=False)
        self.assertEqual(LessonOccurrence.objects.count(), 1)
        self.assertEqual(LessonAttendanceRecord.objects.count(), 1)
        self.assertEqual(LessonAssignment.objects.count(), 1)
        self.assertEqual(report.occurrences_existing, 1)
        self.assertEqual(LessonAttendanceRecord.objects.get().status, LessonAttendanceRecord.Status.EXCUSED)
        self.assertEqual(LessonAssignment.objects.get().notes, "Operational note")

    def test_both_group_derives_single_level_from_roster(self):
        self.group.team_level = LessonGroup.TeamLevel.BOTH
        self.group.save(update_fields=["team_level"])
        report = convert_legacy_iea_lessons(season=self.season, dry_run=False)
        self.assertEqual(report.issue_count, 0)
        self.assertEqual(IEALessonSeriesContext.objects.get().team_level, IEALessonSeriesContext.TeamLevel.UPPER)

    def test_mixed_futures_and_upper_lesson_splits_into_two_occurrences(self):
        self.group.team_level = LessonGroup.TeamLevel.BOTH
        self.group.name = "Combined Tuesday"
        self.group.save(update_fields=["team_level", "name"])
        futures_rider, futures_person, _ = self._add_futures_rider()

        report = convert_legacy_iea_lessons(season=self.season, dry_run=False)

        self.assertEqual(report.issue_count, 0)
        self.assertEqual(report.lessons_convertible, 1)
        self.assertEqual(report.occurrences_created, 2)
        self.assertEqual(LessonOccurrence.objects.count(), 2)
        contexts = {context.team_level: context for context in IEALessonSeriesContext.objects.select_related("series")}
        self.assertEqual(set(contexts), {IEALessonSeriesContext.TeamLevel.FUTURES, IEALessonSeriesContext.TeamLevel.UPPER})
        self.assertIn("Futures", contexts[IEALessonSeriesContext.TeamLevel.FUTURES].series.name)
        self.assertIn("Upper", contexts[IEALessonSeriesContext.TeamLevel.UPPER].series.name)

        futures_occurrence = contexts[IEALessonSeriesContext.TeamLevel.FUTURES].series.occurrences.get()
        upper_occurrence = contexts[IEALessonSeriesContext.TeamLevel.UPPER].series.occurrences.get()
        self.assertEqual(futures_occurrence.starts_at, self.lesson.starts_at)
        self.assertEqual(upper_occurrence.starts_at, self.lesson.starts_at)
        self.assertEqual(list(futures_occurrence.attendance_records.values_list("person_id", flat=True)), [futures_person.id])
        self.assertEqual(list(upper_occurrence.attendance_records.values_list("person_id", flat=True)), [self.person.id])
        self.assertFalse(futures_occurrence.attendance_records.filter(person=self.person).exists())
        self.assertFalse(upper_occurrence.attendance_records.filter(person=futures_person).exists())

    def test_mixed_split_preserves_shared_occurrence_details_and_status(self):
        self.group.team_level = LessonGroup.TeamLevel.BOTH
        self.group.save(update_fields=["team_level"])
        self._add_futures_rider()
        self.lesson.cancelled = True
        self.lesson.save(update_fields=["cancelled"])
        convert_legacy_iea_lessons(season=self.season, dry_run=False)
        for occurrence in LessonOccurrence.objects.all():
            self.assertEqual(occurrence.title, self.lesson.title)
            self.assertEqual(occurrence.starts_at, self.lesson.starts_at)
            self.assertEqual(occurrence.ends_at, self.lesson.ends_at)
            self.assertEqual(occurrence.location, self.lesson.location)
            self.assertEqual(occurrence.notes, self.lesson.notes)
            self.assertEqual(occurrence.status, LessonOccurrence.Status.CANCELLED)

    def test_mixed_split_is_idempotent(self):
        self.group.team_level = LessonGroup.TeamLevel.BOTH
        self.group.save(update_fields=["team_level"])
        self._add_futures_rider()
        first = convert_legacy_iea_lessons(season=self.season, dry_run=False)
        second = convert_legacy_iea_lessons(season=self.season, dry_run=False)
        self.assertEqual(first.occurrences_created, 2)
        self.assertEqual(second.occurrences_created, 0)
        self.assertEqual(second.occurrences_existing, 2)
        self.assertEqual(LessonOccurrence.objects.count(), 2)
        self.assertEqual(LessonAttendanceRecord.objects.count(), 2)
        self.assertEqual(LessonAssignment.objects.count(), 2)

    def test_dry_run_accepts_mixed_lesson_without_writing(self):
        self.group.team_level = LessonGroup.TeamLevel.BOTH
        self.group.save(update_fields=["team_level"])
        self._add_futures_rider()
        report = convert_legacy_iea_lessons(season=self.season, dry_run=True)
        self.assertEqual(report.lessons_convertible, 1)
        self.assertEqual(report.issue_count, 0)
        self.assertEqual(LessonOccurrence.objects.count(), 0)

    def test_missing_person_bridge_is_reported_not_partially_converted(self):
        unlinked = Rider.objects.create(team=self.team, first_name="No", last_name="Bridge", grade=10)
        SeasonMembership.objects.create(rider=unlinked, season=self.season, team_level=SeasonMembership.TeamLevel.UPPER)
        LessonAttendance.objects.create(lesson=self.lesson, rider=unlinked)
        report = convert_legacy_iea_lessons(season=self.season, dry_run=False)
        self.assertEqual(report.issue_count, 1)
        self.assertIn("canonical Person link", report.issues[0].message)
        self.assertEqual(LessonOccurrence.objects.count(), 0)

    def test_missing_team_membership_is_reported_not_guessed(self):
        rider = Rider.objects.create(team=self.team, first_name="No", last_name="Membership", grade=7)
        person = Person.objects.create(team=self.team, first_name="No", last_name="Membership")
        LegacyPersonLink.objects.create(person=person, rider=rider)
        LessonAttendance.objects.create(lesson=self.lesson, rider=rider)
        report = convert_legacy_iea_lessons(season=self.season, dry_run=False)
        self.assertEqual(report.issue_count, 1)
        self.assertIn("no Futures/Upper membership", report.issues[0].message)
        self.assertEqual(LessonOccurrence.objects.count(), 0)

    def test_management_command_defaults_to_dry_run(self):
        call_command("convert_legacy_iea_lessons", season_id=self.season.id)
        self.assertEqual(LessonOccurrence.objects.count(), 0)

    def test_management_command_apply_writes_conversion(self):
        call_command("convert_legacy_iea_lessons", season_id=self.season.id, apply=True)
        self.assertEqual(LessonOccurrence.objects.count(), 1)
