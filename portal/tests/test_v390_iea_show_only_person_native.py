from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase

from portal.iea_voc import voc_candidates
from portal.model_modules.competition_iea import (
    IEAClassCatalogEntry,
    IEASeasonCatalogConfiguration,
)
from portal.model_modules.people import IEAParticipant, Person
from portal.models import (
    Season,
    SeasonClass,
    SeasonMembership,
    Show,
    ShowClass,
    ShowEntry,
    ShowResult,
    Team,
)


class V390IEAShowOnlyPersonNativeTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Person Native Show Only", discipline="hunt_seat")
        self.season = Season.objects.create(
            team=self.team,
            name="2026-2027",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 4, 30),
            is_active=True,
        )
        IEASeasonCatalogConfiguration.objects.create(
            season=self.season,
            rulebook_season="2026-2027",
            disciplines=["hunt_seat"],
        )
        self.h1_catalog = IEAClassCatalogEntry.objects.get(
            rulebook_season="2026-2027", discipline="hunt_seat", class_code="H1"
        )
        self.h2_catalog = IEAClassCatalogEntry.objects.get(
            rulebook_season="2026-2027", discipline="hunt_seat", class_code="H2"
        )
        self.voc_catalog = IEAClassCatalogEntry.objects.get(
            rulebook_season="2026-2027", discipline="hunt_seat", class_code="VOC"
        )
        self.warmup_catalog = IEAClassCatalogEntry.objects.get(
            rulebook_season="2026-2027", discipline="hunt_seat", class_code="H7x/H8x"
        )
        self.h1 = SeasonClass.objects.create(
            season=self.season, name=self.h1_catalog.official_name, team_level="upper",
            discipline="hunt_seat", class_code="H1", catalog_entry=self.h1_catalog,
        )
        self.h2 = SeasonClass.objects.create(
            season=self.season, name=self.h2_catalog.official_name, team_level="upper",
            discipline="hunt_seat", class_code="H2", catalog_entry=self.h2_catalog,
        )
        self.h7 = SeasonClass.objects.create(
            season=self.season, name="Beginner Walk/Trot/Canter", team_level="upper",
            discipline="hunt_seat", class_code="H7",
        )
        self.show = Show.objects.create(
            team=self.team, season=self.season, name="Person Native Show Only",
            show_date=date(2026, 10, 10), competition_level=Show.CompetitionLevel.REGULAR,
        )
        self.h1_show = ShowClass.objects.create(show=self.show, season_class=self.h1, name=self.h1.name, class_number="H1")
        self.h2_show = ShowClass.objects.create(show=self.show, season_class=self.h2, name=self.h2.name, class_number="H2")
        self.h7_show = ShowClass.objects.create(show=self.show, season_class=self.h7, name=self.h7.name, class_number="H7")
        self.voc_show = ShowClass.objects.create(show=self.show, catalog_entry=self.voc_catalog, name=self.voc_catalog.official_name, class_number="VOC")
        self.warmup_show = ShowClass.objects.create(show=self.show, catalog_entry=self.warmup_catalog, name=self.warmup_catalog.official_name, class_number=self.warmup_catalog.class_code)

    def _participant(self, first="Alex"):
        person = Person.objects.create(team=self.team, first_name=first, last_name="Morgan")
        participant = IEAParticipant.objects.create(team=self.team, person=person, active=True)
        membership = SeasonMembership.objects.create(
            iea_participant=participant,
            season=self.season,
            team_level=SeasonMembership.TeamLevel.UPPER,
        )
        return person, participant, membership

    def test_person_native_warmup_requires_and_accepts_prerequisite(self):
        _person, participant, membership = self._participant()
        membership.classes.add(self.h7)
        warmup = ShowEntry(show_class=self.warmup_show, iea_participant=participant)
        with self.assertRaises(ValidationError):
            warmup.full_clean()
        prerequisite = ShowEntry(show_class=self.h7_show, iea_participant=participant, status=ShowEntry.Status.ENTERED)
        prerequisite.full_clean()
        prerequisite.save()
        warmup.full_clean()

    def test_person_native_voc_candidate_and_entry_without_legacy_rider(self):
        person, participant, membership = self._participant()
        membership.classes.set([self.h1, self.h2])
        h1_entry = ShowEntry(show_class=self.h1_show, iea_participant=participant)
        h1_entry.full_clean()
        h1_entry.save()
        h2_entry = ShowEntry(show_class=self.h2_show, iea_participant=participant)
        h2_entry.full_clean()
        h2_entry.save()
        ShowResult.objects.create(entry=h1_entry, place=1)
        ShowResult.objects.create(entry=h2_entry, place=2)

        candidates = voc_candidates(self.show)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].person_id, person.pk)
        self.assertIsNone(candidates[0].rider_id)

        voc_entry = ShowEntry(show_class=self.voc_show, iea_participant=participant)
        voc_entry.full_clean()
        self.assertEqual(voc_entry.entry_type, ShowEntry.EntryType.INDIVIDUAL)
        self.assertFalse(voc_entry.is_point_rider)

    def test_person_native_voc_rejects_participant_without_results(self):
        _person, participant, _membership = self._participant()
        voc_entry = ShowEntry(show_class=self.voc_show, iea_participant=participant)
        with self.assertRaisesMessage(ValidationError, "not currently eligible for VOC"):
            voc_entry.full_clean()
