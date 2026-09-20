from datetime import date
from decimal import Decimal

from django.test import TestCase

from portal.model_modules.finance import Budget, BudgetLine, FinanceDomain
from portal.models import FinancialCategory, FinancialTransaction, Season, Show, ShowBudgetLine, Team
from portal.services.finance_budget_compat import sync_show_budget_to_generic


class V374ShowBudgetCompatibilityTests(TestCase):
    def setUp(self):
        self.team=Team.objects.create(name="Show Budget Barn")
        self.season=Season.objects.create(team=self.team,name="2026",start_date=date(2026,8,1),end_date=date(2027,5,31))
        self.show=Show.objects.create(team=self.team,season=self.season,name="Fall Show",show_date=date(2026,10,10))
        self.category=FinancialCategory.objects.create(team=self.team,name="Entries",kind=FinancialCategory.Kind.EXPENSE)

    def test_sync_creates_iea_generic_show_budget(self):
        ShowBudgetLine.objects.create(show=self.show,category=self.category,kind=FinancialTransaction.Kind.EXPENSE,description="Entry fees",amount=Decimal("250.00"))
        budget=sync_show_budget_to_generic(show=self.show)
        self.assertEqual(budget.finance_domain,FinanceDomain.IEA)
        self.assertEqual(budget.season,self.season)
        line=budget.lines.get(category=self.category,kind=FinancialTransaction.Kind.EXPENSE)
        self.assertEqual(line.amount,Decimal("250.00"))
        self.assertIn("Entry fees",line.description)

    def test_sync_updates_existing_category_kind_without_duplicate(self):
        ShowBudgetLine.objects.create(show=self.show,category=self.category,kind=FinancialTransaction.Kind.EXPENSE,description="Entry fees",amount=Decimal("250.00"))
        budget=sync_show_budget_to_generic(show=self.show)
        legacy=self.show.show_budget_lines.get()
        legacy.amount=Decimal("300.00");legacy.description="Updated entries";legacy.save()
        sync_show_budget_to_generic(show=self.show)
        self.assertEqual(budget.lines.filter(category=self.category,kind=FinancialTransaction.Kind.EXPENSE).count(),1)
        line=budget.lines.get(category=self.category,kind=FinancialTransaction.Kind.EXPENSE)
        self.assertEqual(line.amount,Decimal("300.00"))
        self.assertIn("Updated entries",line.description)

    def test_sync_does_not_delete_generic_only_lines(self):
        ShowBudgetLine.objects.create(show=self.show,category=self.category,kind=FinancialTransaction.Kind.EXPENSE,description="Entry fees",amount=Decimal("250.00"))
        budget=sync_show_budget_to_generic(show=self.show)
        other=FinancialCategory.objects.create(team=self.team,name="Travel",kind=FinancialCategory.Kind.EXPENSE)
        BudgetLine.objects.create(budget=budget,category=other,kind=FinancialTransaction.Kind.EXPENSE,description="Travel planning",amount=Decimal("100.00"))
        sync_show_budget_to_generic(show=self.show)
        self.assertTrue(budget.lines.filter(category=other).exists())

    def test_separate_shows_get_separate_generic_budgets(self):
        other_show=Show.objects.create(team=self.team,season=self.season,name="Winter Show",show_date=date(2026,12,5))
        first=sync_show_budget_to_generic(show=self.show);second=sync_show_budget_to_generic(show=other_show)
        self.assertNotEqual(first.pk,second.pk)
        self.assertEqual(Budget.objects.filter(team=self.team,finance_domain=FinanceDomain.IEA).count(),2)


    def test_sync_aggregates_multiple_legacy_rows_for_same_category_and_kind(self):
        ShowBudgetLine.objects.create(show=self.show,scope=ShowBudgetLine.Scope.PARTICIPATION,category=self.category,kind=FinancialTransaction.Kind.EXPENSE,description="Rider entries",amount=Decimal("250.00"),notes="Participation estimate")
        ShowBudgetLine.objects.create(show=self.show,scope=ShowBudgetLine.Scope.HOSTING,category=self.category,kind=FinancialTransaction.Kind.EXPENSE,description="Host entries",amount=Decimal("125.00"),notes="Hosting estimate")
        budget=sync_show_budget_to_generic(show=self.show)
        lines=budget.lines.filter(category=self.category,kind=FinancialTransaction.Kind.EXPENSE)
        self.assertEqual(lines.count(),1)
        line=lines.get()
        self.assertEqual(line.amount,Decimal("375.00"))
        self.assertIn("2 legacy show budget lines",line.description)
        self.assertIn("Participation estimate",line.notes)
        self.assertIn("Hosting estimate",line.notes)
