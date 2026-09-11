from datetime import date, time

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.models import (
    CommitteeAssignment,
    Season,
    SeasonClass,
    SeasonMembership,
    Show,
    ShowClass,
    Team,
    UserProfile,
)
from portal.views import _show_schedule_edit_levels


class PrizeListScheduleTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Test Team", short_name="TT")
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
            name="Fall IEA Show",
            show_date=date(2026, 10, 10),
            status=Show.Status.ENTERED,
        )
        self.futures_sc = SeasonClass.objects.create(
            season=self.season,
            name="Futures Beginner Flat",
            team_level=SeasonClass.TeamLevel.FUTURES,
            sort_order=1,
        )
        self.upper_sc = SeasonClass.objects.create(
            season=self.season,
            name="Upper Intermediate Flat",
            team_level=SeasonClass.TeamLevel.UPPER,
            sort_order=2,
        )
        self.futures_class = ShowClass.objects.create(
            show=self.show,
            season_class=self.futures_sc,
            class_number="H10",
            sort_order=1,
            prize_list_time=time(9, 0),
        )
        self.upper_class = ShowClass.objects.create(
            show=self.show,
            season_class=self.upper_sc,
            class_number="H12",
            sort_order=2,
            prize_list_time=time(9, 40),
        )

        self.coach = self.make_user("coach", UserProfile.Role.COACH)
        self.futures_parent = self.make_user("futureschair", UserProfile.Role.PARENT)
        self.upper_parent = self.make_user("upperchair", UserProfile.Role.PARENT)
        self.secretary = self.make_user("secretary", UserProfile.Role.PARENT)
        self.rider = self.make_user("rider", UserProfile.Role.RIDER)

        CommitteeAssignment.objects.create(
            team=self.team, season=self.season, user=self.futures_parent,
            role=CommitteeAssignment.Role.FUTURES_PARENT, active=True,
        )
        CommitteeAssignment.objects.create(
            team=self.team, season=self.season, user=self.upper_parent,
            role=CommitteeAssignment.Role.UPPER_PARENT, active=True,
        )
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

    def test_futures_team_parent_can_edit_only_futures_schedule(self):
        levels = _show_schedule_edit_levels(self.futures_parent, self.show)
        self.assertIn(SeasonMembership.TeamLevel.FUTURES, levels)
        self.assertNotIn(SeasonMembership.TeamLevel.UPPER, levels)

        self.client.force_login(self.futures_parent)
        response = self.client.post(reverse("show_schedule", args=[self.show.pk]), {
            "schedule_action": "save",
            f"order_{self.futures_class.pk}": "1",
            f"prize_{self.futures_class.pk}": "09:05",
            f"estimate_{self.futures_class.pk}": "09:20",
            f"note_{self.futures_class.pk}": "Ring 1",
            f"order_{self.upper_class.pk}": "2",
            f"prize_{self.upper_class.pk}": "10:00",
            f"estimate_{self.upper_class.pk}": "10:30",
            f"note_{self.upper_class.pk}": "Should not change",
        })
        self.assertEqual(response.status_code, 302)

        self.futures_class.refresh_from_db()
        self.upper_class.refresh_from_db()
        self.assertEqual(self.futures_class.prize_list_time, time(9, 5))
        self.assertEqual(self.futures_class.estimated_time, time(9, 20))
        self.assertEqual(self.futures_class.schedule_note, "Ring 1")
        self.assertEqual(self.upper_class.prize_list_time, time(9, 40))
        self.assertIsNone(self.upper_class.estimated_time)
        self.assertEqual(self.upper_class.schedule_note, "")

    def test_secretary_can_edit_schedule_for_both_teams(self):
        levels = _show_schedule_edit_levels(self.secretary, self.show)
        self.assertIn(SeasonMembership.TeamLevel.FUTURES, levels)
        self.assertIn(SeasonMembership.TeamLevel.UPPER, levels)

        self.client.force_login(self.secretary)
        response = self.client.post(reverse("show_schedule", args=[self.show.pk]), {
            "schedule_action": "save",
            f"order_{self.futures_class.pk}": "1",
            f"prize_{self.futures_class.pk}": "09:00",
            f"estimate_{self.futures_class.pk}": "09:15",
            f"note_{self.futures_class.pk}": "",
            f"order_{self.upper_class.pk}": "2",
            f"prize_{self.upper_class.pk}": "09:40",
            f"estimate_{self.upper_class.pk}": "10:00",
            f"note_{self.upper_class.pk}": "",
        })
        self.assertEqual(response.status_code, 302)
        self.upper_class.refresh_from_db()
        self.assertEqual(self.upper_class.estimated_time, time(10, 0))

    def test_shift_from_selected_class_preserves_prize_list_baseline(self):
        self.futures_class.estimated_time = time(9, 10)
        self.futures_class.save(update_fields=["estimated_time"])
        self.upper_class.estimated_time = time(9, 50)
        self.upper_class.save(update_fields=["estimated_time"])

        self.client.force_login(self.coach)
        response = self.client.post(reverse("show_schedule", args=[self.show.pk]), {
            "schedule_action": "shift",
            "start_class": str(self.upper_class.pk),
            "shift_minutes": "15",
        })
        self.assertEqual(response.status_code, 302)

        self.futures_class.refresh_from_db()
        self.upper_class.refresh_from_db()
        self.assertEqual(self.futures_class.estimated_time, time(9, 10))
        self.assertEqual(self.upper_class.estimated_time, time(10, 5))
        self.assertEqual(self.upper_class.prize_list_time, time(9, 40))

    def test_reset_estimates_uses_prize_list_times(self):
        self.futures_class.estimated_time = time(10, 0)
        self.futures_class.save(update_fields=["estimated_time"])

        self.client.force_login(self.coach)
        response = self.client.post(reverse("show_schedule", args=[self.show.pk]), {
            "schedule_action": "reset_estimates",
        })
        self.assertEqual(response.status_code, 302)

        self.futures_class.refresh_from_db()
        self.assertEqual(self.futures_class.estimated_time, time(9, 0))

    def test_rider_has_read_only_schedule_even_with_bad_parent_assignment(self):
        CommitteeAssignment.objects.create(
            team=self.team, season=self.season, user=self.rider,
            role=CommitteeAssignment.Role.FUTURES_PARENT, active=True,
        )
        self.assertEqual(_show_schedule_edit_levels(self.rider, self.show), set())

        self.client.force_login(self.rider)
        response = self.client.get(reverse("show_schedule", args=[self.show.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Save schedule")

        post = self.client.post(reverse("show_schedule", args=[self.show.pk]), {
            "schedule_action": "shift",
            "shift_minutes": "15",
        })
        self.assertEqual(post.status_code, 403)
