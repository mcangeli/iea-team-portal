from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase

from portal.model_modules.people import IEAParticipant, Person
from portal.models import (
    Season,
    SeasonClass,
    SeasonMembership,
    Show,
    ShowClass,
    ShowEntry,
    Team,
)


class V390ShowEntryPersonNativeTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Person Native Show Barn")
        self.season = Season.objects.create(
            team=self.team,
            name="2026-2027",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 6, 30),
            is_active=True,
        )
        self.season_class = SeasonClass.objects.create(
            season=self.season,
            name="Upper Open",
            class_code="H1",
            team_level=SeasonClass.TeamLevel.UPPER,
            discipline="hunt_seat",
            active=True,
        )
        self.show = Show.objects.create(
            team=self.team,
            season=self.season,
            name="Person Native Show",
            show_date=date(2026, 10, 1),
        )
        self.show_class = ShowClass.objects.create(
            show=self.show,
            season_class=self.season_class,
            name=self.season_class.name,
            discipline=self.season_class.discipline,
            class_number=self.season_class.class_code,
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
        self.membership.classes.add(self.season_class)

    def test_show_entry_validates_without_legacy_rider(self):
        entry = ShowEntry(
            show_class=self.show_class,
            iea_participant=self.participant,
            status=ShowEntry.Status.PLANNED,
        )
        entry.full_clean()
        entry.save()
        self.assertIsNone(entry.rider_id)
        self.assertEqual(entry.iea_participant.person, self.person)

    def test_show_entry_rejects_unrostered_person_native_participant(self):
        other_person = Person.objects.create(
            team=self.team,
            first_name="Taylor",
            last_name="Jordan",
        )
        other = IEAParticipant.objects.create(
            team=self.team,
            person=other_person,
            active=True,
        )
        entry = ShowEntry(show_class=self.show_class, iea_participant=other)
        with self.assertRaises(ValidationError):
            entry.full_clean()

    def test_show_entry_rejects_wrong_team_level_without_legacy_rider(self):
        self.membership.team_level = SeasonMembership.TeamLevel.FUTURES
        self.membership.save(update_fields=["team_level"])
        entry = ShowEntry(show_class=self.show_class, iea_participant=self.participant)
        with self.assertRaises(ValidationError):
            entry.full_clean()

    def test_show_entry_rejects_unassigned_class_without_legacy_rider(self):
        self.membership.classes.clear()
        entry = ShowEntry(show_class=self.show_class, iea_participant=self.participant)
        with self.assertRaises(ValidationError):
            entry.full_clean()

    def test_person_native_entry_unique_per_class_and_track(self):
        ShowEntry.objects.create(
            show_class=self.show_class,
            iea_participant=self.participant,
            status=ShowEntry.Status.PLANNED,
        )
        duplicate = ShowEntry(
            show_class=self.show_class,
            iea_participant=self.participant,
            status=ShowEntry.Status.PLANNED,
        )
        with self.assertRaises(ValidationError):
            duplicate.full_clean()
