from datetime import date, datetime, timezone as dt_timezone

from django.core.exceptions import ValidationError
from django.test import TestCase

from portal.model_modules.lessons import IEALessonOccurrenceParticipant, IEALessonSeriesContext, LessonEnrollment, LessonOccurrence, LessonProgram, LessonSeries
from portal.model_modules.people import LegacyPersonLink, Person
from portal.models import Rider, Season, SeasonMembership, Team
from portal.services.lesson_preparation import prepare_lesson_occurrence


class IEALessonPreparationTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="IEA Lesson Barn")
        self.season = Season.objects.create(
            team=self.team, name="2026-2027", start_date=date(2026, 8, 1), end_date=date(2027, 6, 30), is_active=True
        )
        self.program = LessonProgram.objects.create(team=self.team, name="Team Instruction")
        self.upper_series = LessonSeries.objects.create(program=self.program, name="Upper Practice")
        IEALessonSeriesContext.objects.create(series=self.upper_series, season=self.season, team_level="upper")
        self.occurrence = LessonOccurrence.objects.create(
            series=self.upper_series,
            title="Upper Practice",
            starts_at=datetime(2026, 9, 22, 21, 0, tzinfo=dt_timezone.utc),
        )

    def _member(self, first_name, last_name, level):
        rider = Rider.objects.create(team=self.team, first_name=first_name, last_name=last_name)
        person = Person.objects.create(team=self.team, first_name=first_name, last_name=last_name)
        LegacyPersonLink.objects.create(person=person, rider=rider)
        SeasonMembership.objects.create(rider=rider, season=self.season, team_level=level)
        return rider, person

    def test_upper_occurrence_uses_upper_season_membership(self):
        _, upper_person = self._member("Uma", "Upper", "upper")
        _, futures_person = self._member("Finn", "Futures", "futures")
        result = prepare_lesson_occurrence(self.occurrence)
        self.assertEqual([row.person for row in result.attendance_created], [upper_person])
        self.assertTrue(self.occurrence.attendance_records.filter(person=upper_person).exists())
        self.assertFalse(self.occurrence.attendance_records.filter(person=futures_person).exists())

    def test_futures_occurrence_uses_futures_membership_only(self):
        futures_series = LessonSeries.objects.create(program=self.program, name="Futures Practice")
        IEALessonSeriesContext.objects.create(series=futures_series, season=self.season, team_level="futures")
        occurrence = LessonOccurrence.objects.create(
            series=futures_series, title="Futures Practice", starts_at=datetime(2026, 9, 23, 21, 0, tzinfo=dt_timezone.utc)
        )
        _, futures_person = self._member("Fran", "Future", "futures")
        _, upper_person = self._member("Uri", "Upper", "upper")
        prepare_lesson_occurrence(occurrence)
        self.assertTrue(occurrence.attendance_records.filter(person=futures_person).exists())
        self.assertFalse(occurrence.attendance_records.filter(person=upper_person).exists())


    def test_explicit_occurrence_roster_can_mix_futures_and_upper(self):
        _, upper_person = self._member("Uma", "Upper", "upper")
        _, futures_person = self._member("Finn", "Futures", "futures")
        _, omitted_person = self._member("Olivia", "Omitted", "upper")
        IEALessonOccurrenceParticipant.objects.create(occurrence=self.occurrence, person=upper_person)
        IEALessonOccurrenceParticipant.objects.create(occurrence=self.occurrence, person=futures_person)
        self.occurrence.iea_roster_configured = True
        self.occurrence.save(update_fields=["iea_roster_configured"])

        prepare_lesson_occurrence(self.occurrence)

        scheduled = set(self.occurrence.attendance_records.values_list("person_id", flat=True))
        self.assertEqual(scheduled, {upper_person.pk, futures_person.pk})
        self.assertNotIn(omitted_person.pk, scheduled)

    def test_intentionally_empty_explicit_roster_does_not_fall_back_to_team(self):
        self._member("Uma", "Upper", "upper")
        self.occurrence.iea_roster_configured = True
        self.occurrence.save(update_fields=["iea_roster_configured"])

        result = prepare_lesson_occurrence(self.occurrence)

        self.assertEqual(result.attendance_created, ())
        self.assertEqual(self.occurrence.attendance_records.count(), 0)
        self.assertEqual(
            self.occurrence.assignments.filter(role="participant").count(), 0
        )

    def test_explicit_roster_requires_active_season_eligibility(self):
        outsider = Person.objects.create(team=self.team, first_name="Not", last_name="Member")
        row = IEALessonOccurrenceParticipant(occurrence=self.occurrence, person=outsider)
        with self.assertRaisesMessage(ValidationError, "eligible rider"):
            row.full_clean()

    def test_iea_preparation_creates_participant_assignment(self):
        _, person = self._member("Riley", "Team", "upper")
        prepare_lesson_occurrence(self.occurrence)
        assignment = self.occurrence.assignments.get(person=person)
        self.assertEqual(assignment.role, "participant")
        self.assertIsNone(assignment.horse_id)

    def test_iea_preparation_is_idempotent(self):
        self._member("Riley", "Team", "upper")
        first = prepare_lesson_occurrence(self.occurrence)
        second = prepare_lesson_occurrence(self.occurrence)
        self.assertEqual(len(first.attendance_created), 1)
        self.assertEqual(len(second.attendance_created), 0)
        self.assertEqual(len(second.attendance_existing), 1)
        self.assertEqual(self.occurrence.attendance_records.count(), 1)
        self.assertEqual(self.occurrence.assignments.count(), 1)

    def test_iea_preparation_requires_canonical_person_bridge(self):
        rider = Rider.objects.create(team=self.team, first_name="Legacy", last_name="Only")
        SeasonMembership.objects.create(rider=rider, season=self.season, team_level="upper")
        with self.assertRaisesMessage(ValidationError, "without canonical Person links"):
            prepare_lesson_occurrence(self.occurrence)
        self.assertEqual(self.occurrence.attendance_records.count(), 0)

    def test_iea_occurrence_must_fall_within_context_season(self):
        self._member("Riley", "Team", "upper")
        outside = LessonOccurrence.objects.create(
            series=self.upper_series, title="Summer Practice", starts_at=datetime(2027, 7, 15, 21, 0, tzinfo=dt_timezone.utc)
        )
        with self.assertRaisesMessage(ValidationError, "within its configured season"):
            prepare_lesson_occurrence(outside)

    def test_iea_preparation_does_not_consume_barn_enrollment(self):
        barn_series = LessonSeries.objects.create(program=self.program, name="Barn Lesson")
        barn_person = Person.objects.create(team=self.team, first_name="Barn", last_name="Student")
        LessonEnrollment.objects.create(series=barn_series, person=barn_person)
        _, team_person = self._member("Team", "Student", "upper")
        prepare_lesson_occurrence(self.occurrence)
        self.assertTrue(self.occurrence.attendance_records.filter(person=team_person).exists())
        self.assertFalse(self.occurrence.attendance_records.filter(person=barn_person).exists())

    def test_barn_preparation_still_uses_lesson_enrollment_not_iea_membership(self):
        barn_series = LessonSeries.objects.create(program=self.program, name="Barn Lesson")
        barn_occurrence = LessonOccurrence.objects.create(
            series=barn_series, title="Barn Lesson", starts_at=datetime(2026, 9, 24, 21, 0, tzinfo=dt_timezone.utc)
        )
        barn_person = Person.objects.create(team=self.team, first_name="Barn", last_name="Student")
        LessonEnrollment.objects.create(series=barn_series, person=barn_person)
        _, team_person = self._member("Team", "Student", "upper")
        prepare_lesson_occurrence(barn_occurrence)
        self.assertTrue(barn_occurrence.attendance_records.filter(person=barn_person).exists())
        self.assertFalse(barn_occurrence.attendance_records.filter(person=team_person).exists())
