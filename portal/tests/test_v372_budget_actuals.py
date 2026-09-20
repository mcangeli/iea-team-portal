from datetime import date
from decimal import Decimal

from django.test import TestCase

from portal.model_modules.finance import Budget, BudgetLine, FinanceDomain
from portal.models import FinancialAccount, FinancialCategory, FinancialTransaction, Team
from portal.services.finance_budgets import budget_actuals


class V372BudgetActualTests(TestCase):
    def setUp(self):
        self.team=Team.objects.create(name="Budget Barn")
        self.income=FinancialCategory.objects.create(team=self.team,name="Board Income",kind=FinancialCategory.Kind.INCOME)
        self.expense=FinancialCategory.objects.create(team=self.team,name="Hay",kind=FinancialCategory.Kind.EXPENSE)
        self.general_bank=FinancialAccount.objects.create(team=self.team,name="Barn Checking",finance_domain=FinanceDomain.GENERAL)
        self.iea_bank=FinancialAccount.objects.create(team=self.team,name="IEA Checking",finance_domain=FinanceDomain.IEA)
        self.budget=Budget.objects.create(team=self.team,finance_domain=FinanceDomain.GENERAL,name="2027 Barn Budget",start_date=date(2027,1,1),end_date=date(2027,12,31),status=Budget.Status.ACTIVE)
        BudgetLine.objects.create(budget=self.budget,category=self.income,kind=FinancialTransaction.Kind.INCOME,description="Board",amount=Decimal("24000.00"))
        BudgetLine.objects.create(budget=self.budget,category=self.expense,kind=FinancialTransaction.Kind.EXPENSE,description="Hay",amount=Decimal("12000.00"))

    def _tx(self,*,kind,category,amount,when=date(2027,2,1),account=None,status=FinancialTransaction.Status.POSTED):
        return FinancialTransaction.objects.create(team=self.team,transaction_date=when,kind=kind,account=account or self.general_bank,category=category,amount=Decimal(amount),description="Budget test",status=status)

    def test_report_compares_planned_and_actual(self):
        self._tx(kind=FinancialTransaction.Kind.INCOME,category=self.income,amount="2000.00")
        self._tx(kind=FinancialTransaction.Kind.EXPENSE,category=self.expense,amount="750.00")
        report=budget_actuals(self.budget)
        self.assertEqual(report.planned_income,Decimal("24000.00"))
        self.assertEqual(report.actual_income,Decimal("2000.00"))
        self.assertEqual(report.planned_expenses,Decimal("12000.00"))
        self.assertEqual(report.actual_expenses,Decimal("750.00"))
        self.assertEqual(report.planned_net,Decimal("12000.00"))
        self.assertEqual(report.actual_net,Decimal("1250.00"))

    def test_report_excludes_other_finance_domain(self):
        self._tx(kind=FinancialTransaction.Kind.EXPENSE,category=self.expense,amount="500.00",account=self.iea_bank)
        report=budget_actuals(self.budget)
        self.assertEqual(report.actual_expenses,ZERO)

    def test_report_excludes_void_and_outside_period(self):
        self._tx(kind=FinancialTransaction.Kind.EXPENSE,category=self.expense,amount="100.00",status=FinancialTransaction.Status.VOID)
        self._tx(kind=FinancialTransaction.Kind.EXPENSE,category=self.expense,amount="200.00",when=date(2028,1,1))
        report=budget_actuals(self.budget)
        self.assertEqual(report.actual_expenses,ZERO)

    def test_line_remaining_and_percent_used(self):
        self._tx(kind=FinancialTransaction.Kind.EXPENSE,category=self.expense,amount="3000.00")
        report=budget_actuals(self.budget)
        row=next(row for row in report.line_rows if row["line"].category_id==self.expense.id)
        self.assertEqual(row["remaining"],Decimal("9000.00"))
        self.assertEqual(row["percent_used"],Decimal("25"))


    def test_period_rows_group_posted_actuals_by_month_and_kind(self):
        FinancialTransaction.objects.create(team=self.team,transaction_date=date(2027,3,4),kind=FinancialTransaction.Kind.EXPENSE,account=self.general_bank,category=self.expense,amount=Decimal("250.00"),description="March hay")
        FinancialTransaction.objects.create(team=self.team,transaction_date=date(2027,3,10),kind=FinancialTransaction.Kind.EXPENSE,account=self.general_bank,category=self.expense,amount=Decimal("150.00"),description="More hay")
        report=budget_actuals(self.budget)
        march=[row for row in report.period_rows if row["month"].month==3 and row["kind"]==FinancialTransaction.Kind.EXPENSE]
        self.assertEqual(len(march),1)
        self.assertEqual(march[0]["actual"],Decimal("400.00"))

    def test_category_rows_group_posted_actuals(self):
        FinancialTransaction.objects.create(team=self.team,transaction_date=date(2027,4,1),kind=FinancialTransaction.Kind.EXPENSE,account=self.general_bank,category=self.expense,amount=Decimal("325.00"),description="Hay")
        report=budget_actuals(self.budget)
        hay=[row for row in report.category_rows if row["category"]==self.expense.name and row["kind"]==FinancialTransaction.Kind.EXPENSE]
        self.assertEqual(len(hay),1)
        self.assertEqual(hay[0]["actual"],Decimal("325.00"))
