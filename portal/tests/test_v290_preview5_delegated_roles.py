from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.models import (
    CommitteeAssignment,
    FinancialAccount,
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


class Preview5DelegatedRoleBoundaryTests(TestCase):
    password = "testpass123"

    def setUp(self):
        self.team = Team.objects.create(name="Arena A", short_name="A")
        self.other_team = Team.objects.create(name="Arena B", short_name="B")
        self.season = Season.objects.create(
            team=self.team,
            name="2026-27",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 7, 31),
            is_active=True,
        )
        self.other_season = Season.objects.create(
            team=self.other_team,
            name="2026-27",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 7, 31),
            is_active=True,
        )
        self.show = Show.objects.create(
            team=self.team,
            season=self.season,
            name="Home IEA Show",
            show_date=date(2026, 10, 10),
        )
        self.other_show_same_team = Show.objects.create(
            team=self.team,
            season=self.season,
            name="Second IEA Show",
            show_date=date(2026, 11, 10),
        )
        self.foreign_show = Show.objects.create(
            team=self.other_team,
            season=self.other_season,
            name="Foreign IEA Show",
            show_date=date(2026, 12, 10),
        )
        self.season_class = SeasonClass.objects.create(
            season=self.season,
            name="Upper Intermediate Flat",
            class_code="H4",
            team_level=SeasonClass.TeamLevel.UPPER,
        )
        self.show_class = ShowClass.objects.create(
            show=self.show,
            season_class=self.season_class,
            class_number="H4",
        )
        self.rider = Rider.objects.create(
            team=self.team,
            first_name="Riley",
            last_name="Test",
            grade=10,
        )
        membership = SeasonMembership.objects.create(
            rider=self.rider,
            season=self.season,
            team_level=SeasonMembership.TeamLevel.UPPER,
        )
        membership.classes.add(self.season_class)
        self.entry = ShowEntry.objects.create(
            show_class=self.show_class,
            rider=self.rider,
            status=ShowEntry.Status.ENTERED,
        )
        self.finance_account = FinancialAccount.objects.create(
            team=self.team,
            name="Operating",
        )

        self.points_secretary = self.make_user("points-secretary", UserProfile.Role.PARENT)
        self.futures_parent = self.make_user("futures-parent", UserProfile.Role.PARENT)
        self.show_lead = self.make_user("show-lead", UserProfile.Role.PARENT)

        CommitteeAssignment.objects.create(
            team=self.team,
            season=self.season,
            user=self.points_secretary,
            role=CommitteeAssignment.Role.POINTS_SECRETARY,
            active=True,
        )
        CommitteeAssignment.objects.create(
            team=self.team,
            season=self.season,
            user=self.futures_parent,
            role=CommitteeAssignment.Role.FUTURES_PARENT,
            active=True,
        )
        ShowLeadAssignment.objects.create(
            show=self.show,
            user=self.show_lead,
            active=True,
        )

    def make_user(self, username, role):
        user = User.objects.create_user(username=username, password=self.password)
        user.profile.team = self.team
        user.profile.role = role
        user.profile.save(update_fields=["team", "role"])
        return user

    def get_as(self, user, route_name, *args):
        self.client.force_login(user)
        return self.client.get(reverse(route_name, args=args))

    def test_points_secretary_can_manage_results_but_not_general_admin(self):
        self.assertEqual(
            self.get_as(self.points_secretary, "show_result_edit", self.entry.pk).status_code,
            200,
        )
        self.assertEqual(
            self.get_as(self.points_secretary, "season_review", self.season.pk).status_code,
            200,
        )
        self.assertEqual(
            self.get_as(self.points_secretary, "show_edit", self.show.pk).status_code,
            403,
        )
        self.assertEqual(
            self.get_as(self.points_secretary, "season_history_import", self.season.pk).status_code,
            403,
        )
        self.assertEqual(
            self.get_as(self.points_secretary, "horse_create").status_code,
            403,
        )
        self.assertEqual(
            self.get_as(self.points_secretary, "finance_account_edit", self.finance_account.pk).status_code,
            403,
        )

    def test_team_parent_coordination_does_not_become_general_management(self):
        self.assertEqual(
            self.get_as(self.futures_parent, "show_planning", self.show.pk).status_code,
            200,
        )
        self.assertEqual(
            self.get_as(self.futures_parent, "show_planning_item_add", self.show.pk).status_code,
            200,
        )
        self.assertEqual(
            self.get_as(self.futures_parent, "show_edit", self.show.pk).status_code,
            403,
        )
        self.assertEqual(
            self.get_as(self.futures_parent, "show_horse_list_upload", self.show.pk).status_code,
            403,
        )
        self.assertEqual(
            self.get_as(self.futures_parent, "finance_account_edit", self.finance_account.pk).status_code,
            403,
        )

    def test_show_lead_authority_is_limited_to_assigned_show(self):
        self.assertEqual(
            self.get_as(self.show_lead, "show_planning", self.show.pk).status_code,
            200,
        )
        self.assertEqual(
            self.get_as(self.show_lead, "show_horse_list_upload", self.show.pk).status_code,
            200,
        )
        self.assertEqual(
            self.get_as(self.show_lead, "show_hoofprint_finalize", self.show.pk).status_code,
            302,
        )
        self.assertEqual(
            self.get_as(self.show_lead, "show_horse_list_upload", self.other_show_same_team.pk).status_code,
            403,
        )
        self.assertEqual(
            self.get_as(self.show_lead, "show_hoofprint_finalize", self.other_show_same_team.pk).status_code,
            403,
        )
        self.assertEqual(
            self.get_as(self.show_lead, "show_edit", self.show.pk).status_code,
            403,
        )
        self.assertEqual(
            self.get_as(self.show_lead, "horse_create").status_code,
            403,
        )
        self.assertEqual(
            self.get_as(self.show_lead, "finance_account_edit", self.finance_account.pk).status_code,
            403,
        )

    def test_delegated_roles_cannot_cross_organization_via_hoofprint_urls(self):
        for user in (self.points_secretary, self.futures_parent, self.show_lead):
            self.assertEqual(
                self.get_as(user, "show_hoofprint", self.foreign_show.pk).status_code,
                404,
            )
            self.assertEqual(
                self.get_as(user, "show_horse_list_upload", self.foreign_show.pk).status_code,
                404,
            )
