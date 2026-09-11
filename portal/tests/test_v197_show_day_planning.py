from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.models import (
    CommitteeAssignment,
    Season,
    Show,
    ShowPlanningItem,
    Team,
    UserProfile,
)


class ShowDayPlanningTests(TestCase):
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
            financial_role=Show.FinancialRole.HOSTING_ATTENDING,
        )
        self.coach = self.make_user("coach", UserProfile.Role.COACH)
        self.futures_parent = self.make_user("futuresparent", UserProfile.Role.PARENT)
        self.upper_parent = self.make_user("upperparent", UserProfile.Role.PARENT)

        CommitteeAssignment.objects.create(
            team=self.team, season=self.season, user=self.futures_parent,
            role=CommitteeAssignment.Role.FUTURES_PARENT, active=True,
        )
        CommitteeAssignment.objects.create(
            team=self.team, season=self.season, user=self.upper_parent,
            role=CommitteeAssignment.Role.UPPER_PARENT, active=True,
        )

    def make_user(self, username, role):
        user = User.objects.create_user(username=username, password="testpass")
        user.profile.team = self.team
        user.profile.role = role
        user.profile.save(update_fields=["team", "role"])
        return user

    def test_hosted_starter_plan_creates_volunteer_items(self):
        self.client.force_login(self.coach)
        response = self.client.post(reverse("show_planning_seed_defaults", args=[self.show.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            ShowPlanningItem.objects.filter(
                show=self.show,
                item_type=ShowPlanningItem.ItemType.VOLUNTEER,
                title="Ring crew",
            ).exists()
        )

    def test_starter_plan_is_duplicate_safe(self):
        self.client.force_login(self.coach)
        self.client.post(reverse("show_planning_seed_defaults", args=[self.show.pk]))
        count = ShowPlanningItem.objects.filter(show=self.show).count()
        self.client.post(reverse("show_planning_seed_defaults", args=[self.show.pk]))
        self.assertEqual(ShowPlanningItem.objects.filter(show=self.show).count(), count)

    def test_futures_team_parent_can_add_only_futures_item(self):
        self.client.force_login(self.futures_parent)
        response = self.client.post(reverse("show_planning_item_add", args=[self.show.pk]), {
            "item_type": ShowPlanningItem.ItemType.VOLUNTEER,
            "team_level": ShowPlanningItem.TeamLevel.FUTURES,
            "category": ShowPlanningItem.Category.TASK,
            "title": "Futures rider check-in helper",
            "quantity": "",
            "details": "",
            "assigned_to": "",
            "sort_order": "10",
            "family_visible": "on",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            ShowPlanningItem.objects.filter(
                show=self.show,
                team_level=ShowPlanningItem.TeamLevel.FUTURES,
                title="Futures rider check-in helper",
            ).exists()
        )

        response = self.client.post(reverse("show_planning_item_add", args=[self.show.pk]), {
            "item_type": ShowPlanningItem.ItemType.VOLUNTEER,
            "team_level": ShowPlanningItem.TeamLevel.UPPER,
            "category": ShowPlanningItem.Category.TASK,
            "title": "Upper-only helper",
            "quantity": "",
            "details": "",
            "assigned_to": "",
            "sort_order": "20",
            "family_visible": "on",
        })
        self.assertNotEqual(response.status_code, 302)
        self.assertFalse(
            ShowPlanningItem.objects.filter(show=self.show, title="Upper-only helper").exists()
        )

    def test_other_team_parent_cannot_edit_futures_item(self):
        item = ShowPlanningItem.objects.create(
            show=self.show,
            item_type=ShowPlanningItem.ItemType.CHECKLIST,
            team_level=ShowPlanningItem.TeamLevel.FUTURES,
            title="Futures paperwork",
        )
        self.client.force_login(self.upper_parent)
        response = self.client.get(reverse("show_planning_item_edit", args=[item.pk]))
        self.assertEqual(response.status_code, 403)

    def test_claimed_volunteer_can_mark_item_done(self):
        item = ShowPlanningItem.objects.create(
            show=self.show,
            item_type=ShowPlanningItem.ItemType.VOLUNTEER,
            team_level=ShowPlanningItem.TeamLevel.ALL,
            title="Water table",
            family_visible=True,
            claimed_by=self.upper_parent,
        )
        self.client.force_login(self.upper_parent)
        response = self.client.post(reverse("show_planning_item_complete", args=[item.pk]))
        self.assertEqual(response.status_code, 302)
        item.refresh_from_db()
        self.assertTrue(item.completed)
