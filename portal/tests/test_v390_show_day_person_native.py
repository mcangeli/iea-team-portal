from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.people import IEAParticipant, Person, PersonRelationship
from portal.models import Season, SeasonClass, SeasonMembership, Show, ShowClass, ShowDayRiderStatus, ShowEntry, Team, UserProfile
from portal.view_modules.show_day_helpers import _show_day_participating_participants


class V390ShowDayPersonNativeTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Person Native Show Day", short_name="PNSD")
        self.season = Season.objects.create(
            team=self.team, name="2026-2027", start_date=date(2026, 8, 1),
            end_date=date(2027, 6, 30), is_active=True,
        )
        self.person = Person.objects.create(
            team=self.team, first_name="No", last_name="Legacy Rider"
        )
        self.participant = IEAParticipant.objects.create(team=self.team, person=self.person)
        self.membership = SeasonMembership.objects.create(
            season=self.season, iea_participant=self.participant,
            team_level=SeasonMembership.TeamLevel.UPPER,
        )
        self.season_class = SeasonClass.objects.create(
            season=self.season, name="Open Flat",
            team_level=SeasonClass.TeamLevel.UPPER, discipline="hunt_seat", class_code="H1",
        )
        self.membership.classes.add(self.season_class)
        self.show = Show.objects.create(
            team=self.team, season=self.season, name="Person Native Show",
            show_date=date(2026, 10, 1),
        )
        self.show_class = ShowClass.objects.create(
            show=self.show, season_class=self.season_class, class_number="H1"
        )
        self.entry = ShowEntry.objects.create(
            show_class=self.show_class, iea_participant=self.participant,
            competition_track=ShowEntry.CompetitionTrack.INDIVIDUAL,
        )

    def test_participating_roster_includes_person_native_entry_without_rider(self):
        participants = list(_show_day_participating_participants(self.show))
        self.assertEqual(participants, [self.participant])
        self.assertIsNone(self.participant.legacy_rider_id)
        self.assertIsNone(self.entry.rider_id)

    def test_show_day_status_accepts_person_native_participant_without_rider(self):
        status = ShowDayRiderStatus(
            show=self.show,
            iea_participant=self.participant,
            status=ShowDayRiderStatus.Status.ARRIVED,
        )
        status.full_clean()
        status.save()

        self.assertIsNone(status.rider_id)
        self.assertEqual(status.participant_identity, self.person)
        self.assertEqual(status.iea_participant_id, self.participant.id)

    def test_parent_relationship_can_update_person_native_show_day_status(self):
        parent_user = User.objects.create_user(username="person-native-parent", password="test-pass")
        UserProfile.objects.create(
            user=parent_user, team=self.team, role=UserProfile.Role.PARENT
        )
        parent = Person.objects.create(
            team=self.team, user=parent_user, first_name="Parent", last_name="Person"
        )
        PersonRelationship.objects.create(
            from_person=parent,
            to_person=self.person,
            relationship_type=PersonRelationship.RelationshipType.PARENT_GUARDIAN,
            active=True,
        )
        self.client.force_login(parent_user)

        response = self.client.post(
            reverse("show_day_rider_status_update", args=[self.show.pk, self.participant.pk]),
            {"status": ShowDayRiderStatus.Status.ARRIVED},
        )

        self.assertEqual(response.status_code, 302)
        status = ShowDayRiderStatus.objects.get(
            show=self.show, iea_participant=self.participant
        )
        self.assertEqual(status.status, ShowDayRiderStatus.Status.ARRIVED)
        self.assertIsNone(status.rider_id)
