from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from portal.model_modules.finance import Budget, BudgetLine, FinanceDomain
from portal.models import FinancialCategory, FinancialTransaction, Season, Team


class V372BudgetFoundationTests(TestCase):
    def setUp(self):
        self.team=Team.objects.create(name="Blue Skies Riding Academy")
        self.other_team=Team.objects.create(name="Other Barn")
        self.expense=FinancialCategory.objects.create(team=self.team,name="Hay",kind=FinancialCategory.Kind.EXPENSE)
        self.income=FinancialCategory.objects.create(team=self.team,name="Board",kind=FinancialCategory.Kind.INCOME)
        self.budget=Budget.objects.create(team=self.team,finance_domain=FinanceDomain.GENERAL,name="2027 Barn Operating Budget",start_date=date(2027,1,1),end_date=date(2027,12,31),status=Budget.Status.DRAFT)

    def test_general_barn_budget_and_lines(self):
        line=BudgetLine(budget=self.budget,category=self.expense,kind=FinancialTransaction.Kind.EXPENSE,description="Hay and forage",amount=Decimal("12000.00"))
        line.full_clean();line.save()
        self.assertEqual(line.amount,Decimal("12000.00"))
        self.assertEqual(self.budget.finance_domain,FinanceDomain.GENERAL)

    def test_budget_rejects_reversed_date_range(self):
        budget=Budget(team=self.team,name="Bad dates",start_date=date(2027,12,31),end_date=date(2027,1,1))
        with self.assertRaises(ValidationError): budget.full_clean()

    def test_budget_season_must_share_organization(self):
        season=Season.objects.create(team=self.other_team,name="Other Season")
        self.budget.season=season
        with self.assertRaises(ValidationError): self.budget.full_clean()

    def test_budget_line_category_must_share_organization(self):
        other=FinancialCategory.objects.create(team=self.other_team,name="Feed",kind=FinancialCategory.Kind.EXPENSE)
        line=BudgetLine(budget=self.budget,category=other,kind=FinancialTransaction.Kind.EXPENSE,description="Feed",amount=Decimal("100.00"))
        with self.assertRaises(ValidationError): line.full_clean()

    def test_budget_line_kind_must_match_category(self):
        line=BudgetLine(budget=self.budget,category=self.income,kind=FinancialTransaction.Kind.EXPENSE,description="Wrong kind",amount=Decimal("100.00"))
        with self.assertRaises(ValidationError): line.full_clean()

    def test_budget_line_amount_cannot_be_negative(self):
        line=BudgetLine(budget=self.budget,category=self.expense,kind=FinancialTransaction.Kind.EXPENSE,description="Hay",amount=Decimal("-1.00"))
        with self.assertRaises(ValidationError): line.full_clean()
