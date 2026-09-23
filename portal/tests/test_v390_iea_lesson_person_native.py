from datetime import date, datetime, timezone as dt_timezone

from django.test import TestCase

from portal.model_modules.lessons import (
    IEALessonOccurrenceParticipant,
    IEALessonSeriesContext,
    LessonOccurrence,
    LessonProgram,
    LessonSeries,
)
from portal.model_modules.people import IEAParticipant, Person
from portal.models import Season, SeasonMembership, Team
from portal.services.lesson_preparation import prepare_lesson_occurrence


class V390IEALessonPersonNativeTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Person Native IEA Barn")
        self.season = Season.objects.create(
            team=self.team,
            name="2026-2027",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 6, 30),
            is_active=True,
        )
        self.program = LessonProgram.objects.create(team=self.team, name="IEA Team Lessons")
        self.series = LessonSeries.objects.create(program=self.program, name="Upper Practice")
        IEALessonSeriesContext.objects.create(
            series=self.series,
            season=self.season,
            team_level=SeasonMembership.TeamLevel.UPPER,
        )
        self.occurrence = LessonOccurrence.objects.create(
            series=self.series,
            title="Upper Practice",
            starts_at=datetime(2026, 9, 23, 21, 0, tzinfo=dt_timezone.utc),
        )
        self.person = Person.objects.create(
            team=self.team,
            first_name="Alex",
            last_name="Morgan",
        )
        self.participant = IEAParticipant.objects.create(
            team=self.team,
            person=self.person,
            active=True,
        )
        self.membership = SeasonMembership.objects.create(
            iea_participant=self.participant,
            season=self.season,
            team_level=SeasonMembership.TeamLevel.UPPER,
        )

    def test_iea_occurrence_participant_validates_without_legacy_rider(self):
        row = IEALessonOccurrenceParticipant(
            occurrence=self.occurrence,
            person=self.person,
        )
        row.full_clean()

    def test_fallback_roster_prepares_without_legacy_rider(self):
        result = prepare_lesson_occurrence(self.occurrence)

        self.assertEqual(
            [row.person for row in result.attendance_created],
            [self.person],
        )
        self.assertTrue(
            self.occurrence.attendance_records.filter(person=self.person).exists()
        )
        self.assertTrue(
            self.occurrence.assignments.filter(
                person=self.person,
                role="participant",
            ).exists()
        )

    def test_explicit_roster_prepares_without_legacy_rider(self):
        IEALessonOccurrenceParticipant.objects.create(
            occurrence=self.occurrence,
            person=self.person,
        )
        self.occurrence.iea_roster_configured = True
        self.occurrence.save(update_fields=["iea_roster_configured"])

        result = prepare_lesson_occurrence(self.occurrence)

        self.assertEqual(
            [row.person for row in result.attendance_created],
            [self.person],
        )
        self.assertEqual(self.occurrence.attendance_records.count(), 1)

    def test_wrong_team_level_is_not_in_fallback_roster(self):
        self.membership.team_level = SeasonMembership.TeamLevel.FUTURES
        self.membership.save(update_fields=["team_level"])

        result = prepare_lesson_occurrence(self.occurrence)

        self.assertEqual(result.attendance_created, ())
        self.assertEqual(self.occurrence.attendance_records.count(), 0)
