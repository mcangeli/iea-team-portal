from django.contrib.auth.models import User
from django.test import TestCase

from portal.forms import RiderAwardForm
from portal.model_modules.people import IEAParticipant, Person
from portal.models import RiderAward, RiderDevelopmentNote, Season, SeasonMembership, Team


class V390PersonHistoryRecordTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Person Native History")
        self.season = Season.objects.create(
            team=self.team,
            name="2026-27",
            start_date="2026-08-01",
            end_date="2027-07-31",
        )
        self.person = Person.objects.create(
            team=self.team,
            first_name="Casey",
            last_name="Participant",
        )
        self.participant = IEAParticipant.objects.create(
            team=self.team,
            person=self.person,
        )
        self.membership = SeasonMembership.objects.create(
            season=self.season,
            iea_participant=self.participant,
            team_level=SeasonMembership.TeamLevel.UPPER,
        )
        self.author = User.objects.create_user(username="history-author")

    def test_award_can_exist_without_legacy_rider(self):
        award = RiderAward(
            season=self.season,
            person=self.person,
            title="Sportsmanship",
            created_by=self.author,
        )
        award.full_clean()
        award.save()

        self.assertIsNone(award.rider_id)
        self.assertEqual(award.participant_identity, self.person)
        self.assertEqual(str(award), "Sportsmanship — Casey Participant")

    def test_development_note_can_exist_without_legacy_rider(self):
        note = RiderDevelopmentNote(
            season=self.season,
            person=self.person,
            author=self.author,
            note="Strong progress in flat work.",
        )
        note.full_clean()
        note.save()

        self.assertIsNone(note.rider_id)
        self.assertEqual(note.participant_identity, self.person)

    def test_award_form_uses_person_native_season_membership(self):
        form = RiderAwardForm(
            data={
                "person": self.person.pk,
                "title": "Most Improved",
                "description": "",
                "presentation_date": "",
                "published": True,
            },
            season=self.season,
        )

        self.assertTrue(form.is_valid(), form.errors)
        award = form.save(commit=False)
        award.season = self.season
        award.created_by = self.author
        award.save()

        self.assertEqual(award.person, self.person)
        self.assertIsNone(award.rider_id)
