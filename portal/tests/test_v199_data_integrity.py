from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.models import (
    FinancialAccount,
    FinancialCategory,
    FinancialTransaction,
    Season,
    Show,
    Team,
    UserProfile,
)


class V199ShowFinanceIntegrityTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Integrity Team")
        self.season = Season.objects.create(
            team=self.team,
            name="2026-27",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 7, 31),
            is_active=True,
            is_closed=False,
        )
        self.admin = User.objects.create_user(username="integrity-admin", password="testpass")
        self.admin.profile.team = self.team
        self.admin.profile.role = UserProfile.Role.ADMIN
        self.admin.profile.save(update_fields=["team", "role"])
        self.client.force_login(self.admin)

        self.show = Show.objects.create(
            team=self.team,
            season=self.season,
            name="Finance Linked Show",
            show_date=date(2026, 10, 10),
        )
        self.account = FinancialAccount.objects.create(
            team=self.team,
            name="Checking",
            account_type=FinancialAccount.AccountType.CHECKING,
            opening_balance=Decimal("0.00"),
        )
        self.category = FinancialCategory.objects.create(
            team=self.team,
            name="Show Fees",
            kind=FinancialCategory.Kind.EXPENSE,
        )

    def test_show_with_financial_transaction_cannot_be_deleted(self):
        FinancialTransaction.objects.create(
            team=self.team,
            season=self.season,
            transaction_date=date(2026, 10, 10),
            kind=FinancialTransaction.Kind.EXPENSE,
            account=self.account,
            category=self.category,
            amount=Decimal("25.00"),
            description="Entry fee",
            show=self.show,
            show_finance_scope=FinancialTransaction.ShowFinanceScope.PARTICIPATION,
        )

        response = self.client.post(
            reverse("show_delete", args=[self.show.pk]),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Show.objects.filter(pk=self.show.pk).exists())
        self.assertContains(response, "cannot be deleted because it is referenced by financial history")

    def test_unlinked_show_can_still_be_deleted(self):
        show = Show.objects.create(
            team=self.team,
            season=self.season,
            name="Disposable Show",
            show_date=date(2026, 11, 1),
        )
        response = self.client.post(reverse("show_delete", args=[show.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Show.objects.filter(pk=show.pk).exists())
