from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.models import (
    GuardianContact,
    Rider,
    RiderGuardian,
    Season,
    SeasonClass,
    SeasonMembership,
    Show,
    ShowClass,
    Team,
    UserProfile,
)
from portal.views import _can_view_private_rider, _can_view_family_account


class Preview5PrivateDataAndExportTests(TestCase):
    def setUp(self):
        self.team_a = Team.objects.create(name="Arena A", short_name="A")
        self.team_b = Team.objects.create(name="Arena B", short_name="B")
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

        self.admin_a = self._user("admin-a-private", self.team_a, UserProfile.Role.ADMIN)
        self.parent_a = self._user("parent-a-private", self.team_a, UserProfile.Role.PARENT)

        self.rider_a = Rider.objects.create(
            team=self.team_a,
            first_name="Alice",
            last_name="Arena",
            email="alice-private@example.com",
            iea_member_number="IEA-A-PRIVATE",
        )
        self.unrelated_rider_a = Rider.objects.create(
            team=self.team_a,
            first_name="Una",
            last_name="Related",
            email="unrelated-private@example.com",
            iea_member_number="IEA-A-OTHER",
        )
        self.rider_b = Rider.objects.create(
            team=self.team_b,
            first_name="Bob",
            last_name="Boundary",
            email="bob-private@example.com",
            iea_member_number="IEA-B-PRIVATE",
        )

        self.guardian_a = GuardianContact.objects.create(
            team=self.team_a,
            user=self.parent_a,
            first_name="Pat",
            last_name="Arena",
            email="parent-a@example.com",
        )
        self.link_a = RiderGuardian.objects.create(
            rider=self.rider_a,
            guardian=self.guardian_a,
            relationship="Parent",
            primary_contact=True,
        )

        self.guardian_b = GuardianContact.objects.create(
            team=self.team_b,
            first_name="Other",
            last_name="Guardian",
        )
        self.link_b = RiderGuardian.objects.create(
            rider=self.rider_b,
            guardian=self.guardian_b,
            relationship="Parent",
        )

        self.membership_a = SeasonMembership.objects.create(
            rider=self.rider_a,
            season=self.season_a,
            team_level=SeasonMembership.TeamLevel.UPPER,
        )
        self.membership_unrelated_a = SeasonMembership.objects.create(
            rider=self.unrelated_rider_a,
            season=self.season_a,
            team_level=SeasonMembership.TeamLevel.UPPER,
        )
        self.membership_b = SeasonMembership.objects.create(
            rider=self.rider_b,
            season=self.season_b,
            team_level=SeasonMembership.TeamLevel.UPPER,
        )

        self.class_b = SeasonClass.objects.create(
            season=self.season_b,
            name="Boundary Class",
            team_level=SeasonClass.TeamLevel.UPPER,
            sort_order=1,
        )
        self.show_b = Show.objects.create(
            team=self.team_b,
            season=self.season_b,
            name="Boundary Show",
            show_date=date(2026, 10, 10),
        )
        self.show_class_b = ShowClass.objects.create(
            show=self.show_b,
            season_class=self.class_b,
            class_number="H99",
            sort_order=1,
        )

    def _user(self, username, team, role):
        user = User.objects.create_user(username=username, password="testpass")
        user.profile.team = team
        user.profile.role = role
        user.profile.save(update_fields=["team", "role"])
        return user

    def test_parent_private_rider_scope_is_family_specific(self):
        self.assertTrue(_can_view_private_rider(self.parent_a, self.rider_a))
        self.assertFalse(_can_view_private_rider(self.parent_a, self.unrelated_rider_a))

    def test_parent_family_account_scope_is_family_specific(self):
        self.assertTrue(_can_view_family_account(self.parent_a, self.membership_a))
        self.assertFalse(_can_view_family_account(self.parent_a, self.membership_unrelated_a))

    def test_parent_can_open_linked_family_account_but_not_foreign_organization(self):
        self.client.force_login(self.parent_a)
        own = self.client.get(reverse("family_account", args=[self.membership_a.pk]))
        foreign = self.client.get(reverse("family_account", args=[self.membership_b.pk]))
        self.assertEqual(own.status_code, 200)
        self.assertEqual(foreign.status_code, 404)

    def test_management_exports_are_not_available_to_parent(self):
        self.client.force_login(self.parent_a)
        self.assertEqual(self.client.get(reverse("rider_export")).status_code, 403)
        self.assertEqual(self.client.get(reverse("parent_export")).status_code, 403)

    def test_finance_exports_are_not_available_to_parent_without_finance_role(self):
        self.client.force_login(self.parent_a)
        self.assertEqual(self.client.get(reverse("finance_transaction_export")).status_code, 403)
        self.assertEqual(self.client.get(reverse("finance_report_receivables_export")).status_code, 403)

    def test_nested_guardian_unlink_cannot_cross_organization(self):
        self.client.force_login(self.admin_a)
        response = self.client.post(
            reverse("rider_guardian_unlink", args=[self.rider_a.pk, self.link_b.pk])
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(RiderGuardian.objects.filter(pk=self.link_b.pk).exists())

    def test_nested_show_class_edit_cannot_cross_organization(self):
        self.client.force_login(self.admin_a)
        response = self.client.get(reverse("show_class_edit", args=[self.show_class_b.pk]))
        self.assertEqual(response.status_code, 404)

    def test_nested_family_charge_create_cannot_cross_organization(self):
        self.client.force_login(self.admin_a)
        response = self.client.get(reverse("family_charge_create", args=[self.membership_b.pk]))
        self.assertEqual(response.status_code, 404)

    def test_private_receipt_lookup_fails_before_file_access_for_foreign_transaction_id(self):
        # The detailed receipt/file tests live in the finance hardening suite. This
        # contract protects the routing expectation here: missing/foreign IDs must
        # not become a storage lookup bypass. A deliberately impossible ID should
        # fail closed as a 404 for an otherwise finance-authorized administrator.
        self.client.force_login(self.admin_a)
        response = self.client.get(reverse("finance_receipt_download", args=[999999999]))
        self.assertEqual(response.status_code, 404)
