from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.horse_models import Horse
from portal.models import FinancialAccount, Rider, Season, Show, Team, UserProfile


class Preview5CrossOrganizationTests(TestCase):
    """Direct-object probes must never cross the current organization boundary."""

    def setUp(self):
        self.team_a = Team.objects.create(name="Organization A")
        self.team_b = Team.objects.create(name="Organization B")
        self.season_a = Season.objects.create(
            team=self.team_a,
            name="2026-27 A",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 7, 31),
            is_active=True,
        )
        self.season_b = Season.objects.create(
            team=self.team_b,
            name="2026-27 B",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 7, 31),
            is_active=True,
        )
        self.admin_a = User.objects.create_user(username="admin-a", password="testpass")
        self.admin_a.profile.team = self.team_a
        self.admin_a.profile.role = UserProfile.Role.ADMIN
        self.admin_a.profile.save(update_fields=["team", "role"])

        self.admin_b = User.objects.create_user(username="admin-b", password="testpass")
        self.admin_b.profile.team = self.team_b
        self.admin_b.profile.role = UserProfile.Role.ADMIN
        self.admin_b.profile.save(update_fields=["team", "role"])

        self.rider_b = Rider.objects.create(team=self.team_b, first_name="Foreign", last_name="Rider")
        self.show_b = Show.objects.create(
            team=self.team_b,
            season=self.season_b,
            name="Foreign Show",
            show_date=date(2026, 11, 1),
        )
        self.horse_b = Horse.objects.create(team=self.team_b, name="Foreign Horse")
        self.account_b = FinancialAccount.objects.create(team=self.team_b, name="Foreign Checking")

        self.client.force_login(self.admin_a)

    def assert_foreign_object_hidden(self, route_name, *args):
        response = self.client.get(reverse(route_name, args=args))
        self.assertEqual(
            response.status_code,
            404,
            f"{route_name} exposed an object owned by another organization",
        )

    def test_people_object_cannot_cross_organization(self):
        self.assert_foreign_object_hidden("rider_detail", self.rider_b.pk)
        self.assert_foreign_object_hidden("rider_edit", self.rider_b.pk)

    def test_horse_object_cannot_cross_organization(self):
        self.assert_foreign_object_hidden("horse_detail", self.horse_b.pk)
        self.assert_foreign_object_hidden("horse_edit", self.horse_b.pk)

    def test_competition_object_cannot_cross_organization(self):
        self.assert_foreign_object_hidden("show_detail", self.show_b.pk)
        self.assert_foreign_object_hidden("show_edit", self.show_b.pk)

    def test_finance_object_cannot_cross_organization(self):
        self.assert_foreign_object_hidden("finance_account_edit", self.account_b.pk)

    def test_administration_cannot_manage_foreign_user(self):
        self.assert_foreign_object_hidden("user_edit", self.admin_b.pk)
        self.assert_foreign_object_hidden("user_reset_password", self.admin_b.pk)

    def test_foreign_season_history_cannot_be_opened(self):
        self.assert_foreign_object_hidden("season_review", self.season_b.pk)
