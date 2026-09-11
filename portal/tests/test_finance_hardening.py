from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from portal.models import (
    CommitteeAssignment, FinancialAccount, FinancialCategory, FinancialTransaction,
    Season, Show, Team, ShowTransactionAllocation,
)
from portal.views import _can_finance, _show_finance_totals
from portal.forms import ShowBudgetLineForm


class FinanceHardeningTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Test Team")
        self.season1 = Season.objects.create(
            team=self.team, name="2026-27", start_date=date(2026, 8, 1),
            end_date=date(2027, 7, 31), is_active=True,
        )
        self.season2 = Season.objects.create(
            team=self.team, name="2025-26", start_date=date(2025, 8, 1),
            end_date=date(2026, 7, 31),
        )
        self.user = User.objects.create_user(username="treasurer", password="testpass")
        CommitteeAssignment.objects.create(
            team=self.team, season=self.season1, user=self.user,
            role=CommitteeAssignment.Role.TREASURER, active=True,
        )
        self.account = FinancialAccount.objects.create(team=self.team, name="Checking")
        self.category = FinancialCategory.objects.create(
            team=self.team, name="Show fees", kind=FinancialCategory.Kind.BOTH
        )

    def test_treasurer_permission_is_season_specific(self):
        self.assertTrue(_can_finance(self.user, self.season1))
        self.assertFalse(_can_finance(self.user, self.season2))

    def test_show_fee_policy_is_configurable_by_competition_level(self):
        self.season1.regular_show_fee_policy = Season.ShowFeePolicy.INCLUDED
        self.season1.regional_show_fee_policy = Season.ShowFeePolicy.FAMILY
        self.assertEqual(
            self.season1.show_fee_policy_for(Show.CompetitionLevel.REGULAR),
            Season.ShowFeePolicy.INCLUDED,
        )
        self.assertEqual(
            self.season1.show_fee_policy_for(Show.CompetitionLevel.REGIONAL),
            Season.ShowFeePolicy.FAMILY,
        )

    def test_hosting_scope_rejected_for_attending_only_show(self):
        show = Show.objects.create(
            team=self.team, season=self.season1, name="Away Show",
            show_date=date(2026, 10, 1),
            financial_role=Show.FinancialRole.ATTENDING,
        )
        tx = FinancialTransaction(
            team=self.team, season=self.season1, transaction_date=date(2026, 10, 1),
            kind=FinancialTransaction.Kind.EXPENSE, account=self.account,
            category=self.category, amount=Decimal("50.00"), description="Expense",
            show=show, show_finance_scope=FinancialTransaction.ShowFinanceScope.HOSTING,
        )
        with self.assertRaises(ValidationError):
            tx.full_clean()

    def test_show_scope_requires_show(self):
        tx = FinancialTransaction(
            team=self.team, season=self.season1, transaction_date=date(2026, 10, 1),
            kind=FinancialTransaction.Kind.EXPENSE, account=self.account,
            category=self.category, amount=Decimal("50.00"), description="Expense",
            show_finance_scope=FinancialTransaction.ShowFinanceScope.PARTICIPATION,
        )
        with self.assertRaises(ValidationError):
            tx.full_clean()

    def test_void_status_retains_transaction_record(self):
        tx = FinancialTransaction.objects.create(
            team=self.team, season=self.season1, transaction_date=date(2026, 10, 1),
            kind=FinancialTransaction.Kind.EXPENSE, account=self.account,
            category=self.category, amount=Decimal("50.00"), description="Expense",
        )
        tx.status = FinancialTransaction.Status.VOID
        tx.void_reason = "Duplicate"
        tx.save()
        self.assertTrue(FinancialTransaction.objects.filter(pk=tx.pk).exists())
        self.assertFalse(
            FinancialTransaction.objects.filter(
                pk=tx.pk, status=FinancialTransaction.Status.POSTED
            ).exists()
        )

    def test_one_payment_can_split_between_two_hosted_shows(self):
        show1 = Show.objects.create(
            team=self.team, season=self.season1, name="Hosted Show A",
            show_date=date(2026, 10, 10),
            financial_role=Show.FinancialRole.HOSTING_ATTENDING,
        )
        show2 = Show.objects.create(
            team=self.team, season=self.season1, name="Hosted Show B",
            show_date=date(2026, 11, 10),
            financial_role=Show.FinancialRole.HOSTING_ATTENDING,
        )
        tx = FinancialTransaction.objects.create(
            team=self.team, season=self.season1, transaction_date=date(2026, 9, 20),
            kind=FinancialTransaction.Kind.EXPENSE, account=self.account,
            category=self.category, amount=Decimal("1200.00"),
            description="Show insurance",
        )
        a1 = ShowTransactionAllocation(
            transaction=tx, show=show1,
            scope=FinancialTransaction.ShowFinanceScope.HOSTING,
            amount=Decimal("600.00"),
        )
        a1.full_clean(); a1.save()
        a2 = ShowTransactionAllocation(
            transaction=tx, show=show2,
            scope=FinancialTransaction.ShowFinanceScope.HOSTING,
            amount=Decimal("600.00"),
        )
        a2.full_clean(); a2.save()

        self.assertEqual(
            _show_finance_totals(show1)["hosting_expense"], Decimal("600.00")
        )
        self.assertEqual(
            _show_finance_totals(show2)["hosting_expense"], Decimal("600.00")
        )
        self.assertEqual(tx.amount, Decimal("1200.00"))

    def test_allocations_cannot_exceed_payment(self):
        show1 = Show.objects.create(
            team=self.team, season=self.season1, name="Hosted Show A",
            show_date=date(2026, 10, 10),
            financial_role=Show.FinancialRole.HOSTING_ATTENDING,
        )
        show2 = Show.objects.create(
            team=self.team, season=self.season1, name="Hosted Show B",
            show_date=date(2026, 11, 10),
            financial_role=Show.FinancialRole.HOSTING_ATTENDING,
        )
        tx = FinancialTransaction.objects.create(
            team=self.team, season=self.season1, transaction_date=date(2026, 9, 20),
            kind=FinancialTransaction.Kind.EXPENSE, account=self.account,
            category=self.category, amount=Decimal("1000.00"),
            description="Shared expense",
        )
        first = ShowTransactionAllocation(
            transaction=tx, show=show1,
            scope=FinancialTransaction.ShowFinanceScope.HOSTING,
            amount=Decimal("700.00"),
        )
        first.full_clean(); first.save()
        second = ShowTransactionAllocation(
            transaction=tx, show=show2,
            scope=FinancialTransaction.ShowFinanceScope.HOSTING,
            amount=Decimal("400.00"),
        )
        with self.assertRaises(ValidationError):
            second.full_clean()

    def test_show_budget_allows_multiple_items_same_category_scope_and_type(self):
        show = Show.objects.create(
            team=self.team, season=self.season1, name="Hosted Show",
            show_date=date(2026, 10, 10),
            financial_role=Show.FinancialRole.HOSTING_ATTENDING,
        )
        from portal.models import ShowBudgetLine
        ShowBudgetLine.objects.create(
            show=show,
            scope=ShowBudgetLine.Scope.HOSTING,
            kind=FinancialTransaction.Kind.EXPENSE,
            category=self.category,
            description="Insurance",
            amount=Decimal("100.00"),
        )
        form = ShowBudgetLineForm(
            data={
                "scope": ShowBudgetLine.Scope.HOSTING,
                "kind": FinancialTransaction.Kind.EXPENSE,
                "category": self.category.pk,
                "description": "Judge fee",
                "amount": "125.00",
                "notes": "",
            },
            show=show,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_show_budget_form_attaches_show_before_model_validation(self):
        show = Show.objects.create(
            team=self.team, season=self.season1, name="Hosted Show",
            show_date=date(2026, 10, 10),
            financial_role=Show.FinancialRole.HOSTING_ATTENDING,
        )
        from portal.models import ShowBudgetLine
        form = ShowBudgetLineForm(
            data={
                "scope": ShowBudgetLine.Scope.HOSTING,
                "kind": FinancialTransaction.Kind.EXPENSE,
                "category": self.category.pk,
                "description": "Insurance",
                "amount": "125.00",
                "notes": "",
            },
            show=show,
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.instance.show, show)

    def test_budget_actual_is_specific_to_budget_item(self):
        from portal.models import ShowBudgetLine
        show = Show.objects.create(
            team=self.team, season=self.season1, name="Hosted Show",
            show_date=date(2026, 10, 10),
            financial_role=Show.FinancialRole.HOSTING_ATTENDING,
        )
        insurance = ShowBudgetLine.objects.create(
            show=show, scope=ShowBudgetLine.Scope.HOSTING,
            kind=FinancialTransaction.Kind.EXPENSE, category=self.category,
            description="Insurance", amount=Decimal("600.00"),
        )
        judge = ShowBudgetLine.objects.create(
            show=show, scope=ShowBudgetLine.Scope.HOSTING,
            kind=FinancialTransaction.Kind.EXPENSE, category=self.category,
            description="Judge fee", amount=Decimal("900.00"),
        )
        tx = FinancialTransaction.objects.create(
            team=self.team, season=self.season1, transaction_date=date(2026, 9, 20),
            kind=FinancialTransaction.Kind.EXPENSE, account=self.account,
            category=self.category, amount=Decimal("500.00"), description="Insurance payment",
        )
        alloc = ShowTransactionAllocation(
            transaction=tx, show=show,
            scope=FinancialTransaction.ShowFinanceScope.HOSTING,
            budget_line=insurance, amount=Decimal("500.00"),
        )
        alloc.full_clean(); alloc.save()
        rows = _show_finance_totals(show)["budget_rows"]
        actuals = {row["line"].description: row["actual"] for row in rows}
        self.assertEqual(actuals["Insurance"], Decimal("500.00"))
        self.assertEqual(actuals["Judge fee"], Decimal("0"))

    def test_show_budget_line_string_is_human_readable(self):
        from portal.models import ShowBudgetLine
        show = Show.objects.create(
            team=self.team, season=self.season1, name="Hosted Show",
            show_date=date(2026, 10, 10),
            financial_role=Show.FinancialRole.HOSTING_ATTENDING,
        )
        line = ShowBudgetLine.objects.create(
            show=show,
            scope=ShowBudgetLine.Scope.HOSTING,
            kind=FinancialTransaction.Kind.EXPENSE,
            category=self.category,
            description="Show insurance",
            amount=Decimal("600.00"),
        )
        self.assertEqual(
            str(line),
            "Show insurance · Show fees · $600.00",
        )

