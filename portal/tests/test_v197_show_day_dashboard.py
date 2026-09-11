from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.models import (
    CommitteeAssignment,
    Rider,
    Season,
    SeasonClass,
    SeasonMembership,
    Show,
    ShowClass,
    ShowDayRiderStatus,
    ShowEntry,
    Team,
    UserProfile,
)


class ShowDayDashboardTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Test Team")
        self.season = Season.objects.create(
            team=self.team, name="2026-27",
            start_date=date(2026, 8, 1), end_date=date(2027, 7, 31),
            is_active=True,
        )
        self.show = Show.objects.create(
            team=self.team, season=self.season,
            name="Fall Show", show_date=date(2026, 10, 10),
            status=Show.Status.ENTERED,
        )
        self.sc = SeasonClass.objects.create(
            season=self.season, name="Futures Flat",
            team_level=SeasonClass.TeamLevel.FUTURES,
        )
        self.show_class = ShowClass.objects.create(
            show=self.show, season_class=self.sc,
            class_number="H10", sort_order=1,
        )
        self.rider = Rider.objects.create(
            team=self.team, first_name="Emma", last_name="Brown", grade=7,
        )
        self.membership = SeasonMembership.objects.create(
            rider=self.rider, season=self.season,
            team_level=SeasonMembership.TeamLevel.FUTURES,
        )
        self.membership.classes.add(self.sc)
        self.entry = ShowEntry.objects.create(
            show_class=self.show_class, rider=self.rider,
            status=ShowEntry.Status.ENTERED,
        )

        self.coach = self.make_user("coach", UserProfile.Role.COACH)
        self.parent = self.make_user("teamparent", UserProfile.Role.PARENT)
        CommitteeAssignment.objects.create(
            team=self.team, season=self.season, user=self.parent,
            role=CommitteeAssignment.Role.FUTURES_PARENT, active=True,
        )
        self.secretary = self.make_user("secretary", UserProfile.Role.PARENT)
        CommitteeAssignment.objects.create(
            team=self.team, season=self.season, user=self.secretary,
            role=CommitteeAssignment.Role.POINTS_SECRETARY, active=True,
        )

    def make_user(self, username, role):
        user = User.objects.create_user(username=username, password="testpass")
        user.profile.team = self.team
        user.profile.role = role
        user.profile.save(update_fields=["team", "role"])
        return user

    def test_team_parent_can_check_in_designated_team_rider(self):
        self.client.force_login(self.parent)
        response = self.client.post(
            reverse("show_day_rider_status_update", args=[self.show.pk, self.rider.pk]),
            {"status": ShowDayRiderStatus.Status.ARRIVED, "note": "At ring"},
        )
        self.assertEqual(response.status_code, 302)
        obj = ShowDayRiderStatus.objects.get(show=self.show, rider=self.rider)
        self.assertEqual(obj.status, ShowDayRiderStatus.Status.ARRIVED)
        self.assertEqual(obj.updated_by, self.parent)

    def test_secretary_dashboard_exposes_result_entry(self):
        self.client.force_login(self.secretary)
        response = self.client.get(reverse("show_day_dashboard", args=[self.show.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("show_result_edit", args=[self.entry.pk]))

    def test_show_day_status_is_unique_per_show_and_rider(self):
        ShowDayRiderStatus.objects.create(
            show=self.show, rider=self.rider,
            status=ShowDayRiderStatus.Status.EXPECTED,
        )
        self.client.force_login(self.coach)
        self.client.post(
            reverse("show_day_rider_status_update", args=[self.show.pk, self.rider.pk]),
            {"status": ShowDayRiderStatus.Status.RUNNING_LATE},
        )
        self.assertEqual(
            ShowDayRiderStatus.objects.filter(show=self.show, rider=self.rider).count(), 1
        )
        self.assertEqual(
            ShowDayRiderStatus.objects.get(show=self.show, rider=self.rider).status,
            ShowDayRiderStatus.Status.RUNNING_LATE,
        )
