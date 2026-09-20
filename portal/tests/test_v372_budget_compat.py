from datetime import date
from decimal import Decimal

from django.test import TestCase

from portal.model_modules.finance import FinanceDomain
from portal.models import FinancialCategory, FinancialTransaction, Season, SeasonBudget, Team
from portal.services.finance_budget_compat import sync_season_budget_to_generic


class V372SeasonBudgetCompatibilityTests(TestCase):
    def setUp(self):
        self.team=Team.objects.create(name="IEA Budget Barn")
        self.season=Season.objects.create(team=self.team,name="2027 IEA",start_date=date(2026,8,1),end_date=date(2027,7,31))
        self.income=FinancialCategory.objects.create(team=self.team,name="Dues",kind=FinancialCategory.Kind.INCOME)
        self.expense=FinancialCategory.objects.create(team=self.team,name="Shows",kind=FinancialCategory.Kind.EXPENSE)
        SeasonBudget.objects.create(season=self.season,category=self.income,kind=FinancialTransaction.Kind.INCOME,amount=Decimal("15000.00"))
        SeasonBudget.objects.create(season=self.season,category=self.expense,kind=FinancialTransaction.Kind.EXPENSE,amount=Decimal("9000.00"),notes="Show costs")

    def test_sync_creates_iea_budget_with_season_period(self):
        budget=sync_season_budget_to_generic(season=self.season)
        self.assertEqual(budget.finance_domain,FinanceDomain.IEA)
        self.assertEqual(budget.season,self.season)
        self.assertEqual(budget.start_date,self.season.start_date)
        self.assertEqual(budget.end_date,self.season.end_date)
        self.assertEqual(budget.lines.count(),2)

    def test_sync_preserves_legacy_amounts_and_notes(self):
        budget=sync_season_budget_to_generic(season=self.season)
        shows=budget.lines.get(category=self.expense,kind=FinancialTransaction.Kind.EXPENSE)
        self.assertEqual(shows.amount,Decimal("9000.00"))
        self.assertEqual(shows.notes,"Show costs")

    def test_sync_is_idempotent_and_updates_amount(self):
        first=sync_season_budget_to_generic(season=self.season)
        legacy=SeasonBudget.objects.get(season=self.season,category=self.expense)
        legacy.amount=Decimal("9500.00");legacy.save()
        second=sync_season_budget_to_generic(season=self.season)
        self.assertEqual(first.pk,second.pk)
        self.assertEqual(second.lines.get(category=self.expense).amount,Decimal("9500.00"))
        self.assertEqual(second.lines.count(),2)
