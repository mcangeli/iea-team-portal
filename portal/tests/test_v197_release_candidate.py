from datetime import date, time

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.models import (
    CommitteeAssignment,
    Rider,
    Season,
    SeasonMembership,
    Show,
    ShowClass,
    ShowDayRiderStatus,
    ShowEntry,
    ShowPlanningItem,
    Team,
    UserProfile,
)


class V197ReleaseCandidateTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Test Team")
        self.season = Season.objects.create(
            team=self.team,
            name="2026-27",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 7, 31),
            is_active=True,
        )
        self.show = Show.objects.create(
            team=self.team,
            season=self.season,
            name="Fall Show",
            show_date=date(2026, 10, 10),
        )

        self.futures_parent = self.make_user(
            "futuresparent", UserProfile.Role.PARENT
        )
        self.secretary = self.make_user(
            "secretary", UserProfile.Role.PARENT
        )
        CommitteeAssignment.objects.create(
            team=self.team,
            season=self.season,
            user=self.futures_parent,
            role=CommitteeAssignment.Role.FUTURES_PARENT,
            active=True,
        )
        CommitteeAssignment.objects.create(
            team=self.team,
            season=self.season,
            user=self.secretary,
            role=CommitteeAssignment.Role.POINTS_SECRETARY,
            active=True,
        )

        self.futures_rider = Rider.objects.create(
            team=self.team, first_name="Emma", last_name="Brown", grade=7
        )
        self.upper_rider = Rider.objects.create(
            team=self.team, first_name="Taylor", last_name="Smith", grade=10
        )
        SeasonMembership.objects.create(
            rider=self.futures_rider,
            season=self.season,
            team_level=SeasonMembership.TeamLevel.FUTURES,
        )
        SeasonMembership.objects.create(
            rider=self.upper_rider,
            season=self.season,
            team_level=SeasonMembership.TeamLevel.UPPER,
        )

        self.futures_class = ShowClass.objects.create(
            show=self.show,
            name="Futures Flat",
            class_number="H12",
            sort_order=10,
            estimated_time=time(10, 0),
        )
        self.upper_class = ShowClass.objects.create(
            show=self.show,
            name="Upper Flat",
            class_number="H20",
            sort_order=20,
            estimated_time=time(11, 0),
        )
        ShowEntry.objects.create(
            show_class=self.futures_class,
            rider=self.futures_rider,
            status=ShowEntry.Status.ENTERED,
        )
        ShowEntry.objects.create(
            show_class=self.upper_class,
            rider=self.upper_rider,
            status=ShowEntry.Status.ENTERED,
        )

    def make_user(self, username, role):
        user = User.objects.create_user(username=username, password="testpass")
        user.profile.team = self.team
        user.profile.role = role
        user.profile.save(update_fields=["team", "role"])
        return user

    def test_futures_team_parent_dashboard_is_squad_scoped(self):
        self.client.force_login(self.futures_parent)
        response = self.client.get(
            reverse("show_day_dashboard", args=[self.show.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Emma")
        self.assertContains(response, "Futures Flat")
        self.assertNotContains(response, "Taylor")
        self.assertNotContains(response, "Upper Flat")

    def test_secretary_dashboard_retains_full_team_scope(self):
        self.client.force_login(self.secretary)
        response = self.client.get(
            reverse("show_day_dashboard", args=[self.show.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Emma")
        self.assertContains(response, "Taylor")
        self.assertContains(response, "Futures Flat")
        self.assertContains(response, "Upper Flat")

    def test_archived_season_blocks_show_day_status_change(self):
        self.futures_rider.guardians.add(self.futures_parent)
        self.season.is_closed = True
        self.season.save(update_fields=["is_closed"])

        self.client.force_login(self.futures_parent)
        response = self.client.post(
            reverse(
                "show_day_rider_status_update",
                args=[self.show.pk, self.futures_rider.pk],
            ),
            {
                "status": ShowDayRiderStatus.Status.ARRIVED,
                "return_to": "my_show_day",
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            ShowDayRiderStatus.objects.filter(
                show=self.show, rider=self.futures_rider
            ).exists()
        )

    def test_archived_season_blocks_planning_completion(self):
        item = ShowPlanningItem.objects.create(
            show=self.show,
            item_type=ShowPlanningItem.ItemType.VOLUNTEER,
            team_level=ShowPlanningItem.TeamLevel.FUTURES,
            category=ShowPlanningItem.Category.TASK,
            title="Lunch helper",
            family_visible=True,
            claimed_by=self.futures_parent,
        )
        self.season.is_closed = True
        self.season.save(update_fields=["is_closed"])

        self.client.force_login(self.futures_parent)
        response = self.client.post(
            reverse("show_planning_item_complete", args=[item.pk])
        )
        self.assertEqual(response.status_code, 403)
        item.refresh_from_db()
        self.assertFalse(item.completed)

    def test_invalid_my_show_day_status_returns_to_my_show_day(self):
        self.futures_rider.guardians.add(self.futures_parent)
        self.client.force_login(self.futures_parent)
        response = self.client.post(
            reverse(
                "show_day_rider_status_update",
                args=[self.show.pk, self.futures_rider.pk],
            ),
            {
                "status": "not-a-real-status",
                "return_to": "my_show_day",
            },
        )
        self.assertRedirects(
            response, reverse("my_show_day", args=[self.show.pk])
        )
