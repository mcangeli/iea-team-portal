from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.public_site import PublicShowPublication
from portal.model_modules.show_day_state import ShowClassLiveState
from portal.models import (
    Rider,
    Season,
    SeasonClass,
    SeasonMembership,
    Show,
    ShowClass,
    ShowEntry,
    ShowLeadAssignment,
    Team,
    UserProfile,
)
from portal.publication import public_show_schedule_payload
from portal.tests.v390_compat import bridge_legacy_rider


class ShowClassLiveStatusTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
        self.season = Season.objects.create(
            team=self.team,
            name="2026-2027",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 6, 30),
            is_active=True,
        )
        self.show = Show.objects.create(
            team=self.team,
            season=self.season,
            name="Autumn Invitational",
            show_date=date(2026, 10, 10),
            status=Show.Status.ENTERED,
        )
        self.season_class = SeasonClass.objects.create(
            season=self.season,
            name="Futures Flat",
            team_level=SeasonClass.TeamLevel.FUTURES,
        )
        self.show_class = ShowClass.objects.create(
            show=self.show,
            season_class=self.season_class,
            name="Futures Flat",
            class_number="H10",
            sort_order=1,
        )
        self.rider = Rider.objects.create(
            team=self.team,
            first_name="Emma",
            last_name="Brown",
            grade=7,
        )
        SeasonMembership.objects.create(
            rider=self.rider,
            season=self.season,
            team_level=SeasonMembership.TeamLevel.FUTURES,
        )
        ShowEntry.objects.create(
            show_class=self.show_class,
            rider=self.rider,
            status=ShowEntry.Status.ENTERED,
        )
        bridge_legacy_rider(self.rider)

        self.admin = self.make_user("class-admin", UserProfile.Role.ADMIN)
        self.coach = self.make_user("class-coach", UserProfile.Role.COACH)
        self.lead = self.make_user("class-lead", UserProfile.Role.PARENT)
        self.parent = self.make_user("class-parent", UserProfile.Role.PARENT)
        ShowLeadAssignment.objects.create(show=self.show, user=self.lead, active=True)

    def make_user(self, username, role, team=None):
        user = User.objects.create_user(username=username, password="testpass")
        user.profile.team = team or self.team
        user.profile.role = role
        user.profile.save(update_fields=["team", "role"])
        return user

    def update_status(self, user, status, show_class=None):
        self.client.force_login(user)
        return self.client.post(
            reverse(
                "show_class_live_status_update",
                args=[(show_class or self.show_class).pk],
            ),
            {"status": status},
        )

    def test_coach_can_start_pause_resume_and_complete_class(self):
        response = self.update_status(self.coach, ShowClassLiveState.Status.IN_PROGRESS)
        self.assertEqual(response.status_code, 302)
        state = ShowClassLiveState.objects.get(show_class=self.show_class)
        self.assertEqual(state.status, ShowClassLiveState.Status.IN_PROGRESS)
        self.assertIsNotNone(state.started_at)
        self.assertIsNone(state.completed_at)
        self.assertEqual(state.updated_by, self.coach)
        self.show.refresh_from_db()
        self.assertEqual(self.show.status, Show.Status.IN_PROGRESS)

        self.update_status(self.coach, ShowClassLiveState.Status.PAUSED)
        state.refresh_from_db()
        self.assertEqual(state.status, ShowClassLiveState.Status.PAUSED)
        started_at = state.started_at

        self.update_status(self.coach, ShowClassLiveState.Status.IN_PROGRESS)
        state.refresh_from_db()
        self.assertEqual(state.status, ShowClassLiveState.Status.IN_PROGRESS)
        self.assertEqual(state.started_at, started_at)

        self.update_status(self.coach, ShowClassLiveState.Status.COMPLETE)
        state.refresh_from_db()
        self.assertEqual(state.status, ShowClassLiveState.Status.COMPLETE)
        self.assertIsNotNone(state.completed_at)

    def test_assigned_show_lead_can_update_class_but_parent_cannot(self):
        response = self.update_status(self.lead, ShowClassLiveState.Status.IN_PROGRESS)
        self.assertEqual(response.status_code, 302)

        ShowClassLiveState.objects.filter(show_class=self.show_class).delete()
        response = self.update_status(self.parent, ShowClassLiveState.Status.IN_PROGRESS)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(ShowClassLiveState.objects.filter(show_class=self.show_class).exists())

    def test_other_organization_cannot_update_class(self):
        other_team = Team.objects.create(name="Other Program")
        other_user = self.make_user("other-class-coach", UserProfile.Role.COACH, team=other_team)
        response = self.update_status(other_user, ShowClassLiveState.Status.IN_PROGRESS)
        self.assertEqual(response.status_code, 404)

    def test_starting_and_completing_class_syncs_public_current_class(self):
        publication = PublicShowPublication.objects.create(
            show=self.show,
            slug="autumn-invitational-live",
            is_published=True,
            publish_schedule=True,
            publish_live_status=True,
        )

        self.update_status(self.admin, ShowClassLiveState.Status.IN_PROGRESS)
        publication.refresh_from_db()
        self.assertEqual(publication.current_class, self.show_class)

        schedule = public_show_schedule_payload(publication)
        self.assertEqual(schedule[0]["state"], "current")
        self.assertEqual(schedule[0]["state_label"], "Now")

        self.update_status(self.admin, ShowClassLiveState.Status.PAUSED)
        publication.refresh_from_db()
        schedule = public_show_schedule_payload(publication)
        self.assertEqual(schedule[0]["state"], "paused")

        self.update_status(self.admin, ShowClassLiveState.Status.COMPLETE)
        publication.refresh_from_db()
        self.assertIsNone(publication.current_class)
        schedule = public_show_schedule_payload(publication)
        self.assertEqual(schedule[0]["state"], "complete")

    def test_dashboard_shows_class_controls_only_to_allowed_roles(self):
        for user in (self.admin, self.coach, self.lead):
            self.client.force_login(user)
            response = self.client.get(reverse("show_day_dashboard", args=[self.show.pk]))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Not started")
            self.assertContains(response, "Start")
            self.assertContains(
                response,
                reverse("show_class_live_status_update", args=[self.show_class.pk]),
            )

        self.client.force_login(self.parent)
        response = self.client.get(reverse("show_day_dashboard", args=[self.show.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Not started")
        self.assertNotContains(
            response,
            reverse("show_class_live_status_update", args=[self.show_class.pk]),
        )
