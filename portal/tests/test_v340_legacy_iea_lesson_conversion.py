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

    def test_mixed_futures_and_upper_roster_is_reported_not_guessed(self):
        self.group.team_level = LessonGroup.TeamLevel.BOTH
        self.group.save(update_fields=["team_level"])
        futures_rider = Rider.objects.create(team=self.team, first_name="Fin", last_name="Future", grade=7)
        futures_person = Person.objects.create(team=self.team, first_name="Fin", last_name="Future")
        LegacyPersonLink.objects.create(person=futures_person, rider=futures_rider)
        SeasonMembership.objects.create(rider=futures_rider, season=self.season, team_level=SeasonMembership.TeamLevel.FUTURES)
        self.group.riders.add(futures_rider)
        LessonAttendance.objects.create(lesson=self.lesson, rider=futures_rider)

        report = convert_legacy_iea_lessons(season=self.season, dry_run=False)
        self.assertEqual(report.issue_count, 1)
        self.assertIn("both Futures and Upper", report.issues[0].message)
        self.assertEqual(LessonOccurrence.objects.count(), 0)

    def test_missing_person_bridge_is_reported_not_partially_converted(self):
        unlinked = Rider.objects.create(team=self.team, first_name="No", last_name="Bridge", grade=10)
        SeasonMembership.objects.create(rider=unlinked, season=self.season, team_level=SeasonMembership.TeamLevel.UPPER)
        LessonAttendance.objects.create(lesson=self.lesson, rider=unlinked)
        report = convert_legacy_iea_lessons(season=self.season, dry_run=False)
        self.assertEqual(report.issue_count, 1)
        self.assertIn("without canonical Person links", report.issues[0].message)
        self.assertEqual(LessonOccurrence.objects.count(), 0)

    def test_management_command_defaults_to_dry_run(self):
        call_command("convert_legacy_iea_lessons", season_id=self.season.id)
        self.assertEqual(LessonOccurrence.objects.count(), 0)

    def test_management_command_apply_writes_conversion(self):
        call_command("convert_legacy_iea_lessons", season_id=self.season.id, apply=True)
        self.assertEqual(LessonOccurrence.objects.count(), 1)
