from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from portal.model_modules.capabilities import OrganizationCapabilityAssignment
from portal.model_modules.finance import FinanceDomain, ReceivableAccount, ReceivableCharge
from portal.model_modules.people import Person
from portal.models import FinancialAccount, FinancialCategory, FinancialTransaction, Season, Team
from portal.services.finance_reports import finance_report_for_user

class FinanceReportingTests(TestCase):
    def setUp(self):
        self.team=Team.objects.create(name="Reporting Barn")
        self.admin=get_user_model().objects.create_user(username="reportadmin",password="pass")
        p=self.admin.profile;p.team=self.team;p.role=p.Role.ADMIN;p.save(update_fields=["team","role"])
        self.general=FinancialAccount.objects.create(team=self.team,name="Operating",finance_domain=FinanceDomain.GENERAL)
        self.iea=FinancialAccount.objects.create(team=self.team,name="IEA",finance_domain=FinanceDomain.IEA)
        self.income=FinancialCategory.objects.create(team=self.team,name="Board",kind=FinancialCategory.Kind.INCOME)
        self.expense=FinancialCategory.objects.create(team=self.team,name="Feed",kind=FinancialCategory.Kind.EXPENSE)
        FinancialTransaction.objects.create(team=self.team,transaction_date=date(2026,9,1),kind="income",account=self.general,category=self.income,amount=Decimal("500.00"),description="Board")
        FinancialTransaction.objects.create(team=self.team,transaction_date=date(2026,9,2),kind="expense",account=self.general,category=self.expense,amount=Decimal("125.00"),description="Feed")
        FinancialTransaction.objects.create(team=self.team,transaction_date=date(2026,9,3),kind="income",account=self.iea,category=self.income,amount=Decimal("75.00"),description="IEA fee")
    def test_report_summarizes_domain_ledger(self):
        report=finance_report_for_user(self.admin,self.team,FinanceDomain.GENERAL,start_date=date(2026,9,1),end_date=date(2026,9,30))
        self.assertEqual(report.income,Decimal("500.00"));self.assertEqual(report.expenses,Decimal("125.00"));self.assertEqual(report.net,Decimal("375.00"))
        self.assertEqual(len(report.category_rows),2)
    def test_report_excludes_void_and_out_of_range_transactions(self):
        FinancialTransaction.objects.create(team=self.team,transaction_date=date(2026,8,1),kind="income",account=self.general,category=self.income,amount=Decimal("900.00"),description="Old")
        FinancialTransaction.objects.create(team=self.team,transaction_date=date(2026,9,4),kind="income",account=self.general,category=self.income,amount=Decimal("300.00"),description="Void",status="void")
        report=finance_report_for_user(self.admin,self.team,FinanceDomain.GENERAL,start_date=date(2026,9,1),end_date=date(2026,9,30))
        self.assertEqual(report.income,Decimal("500.00"))
    def test_report_includes_receivables_and_overdue_balance(self):
        account=ReceivableAccount.objects.create(team=self.team,name="Family",finance_domain=FinanceDomain.GENERAL)
        ReceivableCharge.objects.create(account=account,description="Board",amount=Decimal("200.00"),charge_date=date(2026,8,1),due_date=date(2026,8,15))
        ReceivableCharge.objects.create(account=account,description="Future",amount=Decimal("50.00"),charge_date=date(2026,9,1),due_date=date(2026,10,1))
        report=finance_report_for_user(self.admin,self.team,FinanceDomain.GENERAL,as_of=date(2026,9,17))
        self.assertEqual(report.receivables,Decimal("250.00"));self.assertEqual(report.overdue_receivables,Decimal("200.00"))
    def test_iea_only_user_cannot_report_general_domain(self):
        user=get_user_model().objects.create_user(username="ieareporter",password="pass");p=user.profile;p.team=self.team;p.save(update_fields=["team"])
        person=Person.objects.create(team=self.team,user=user,first_name="IEA",last_name="Treasurer")
        OrganizationCapabilityAssignment.objects.create(team=self.team,person=person,capability=OrganizationCapabilityAssignment.Capability.MANAGE_IEA_FINANCE)
        self.assertIsNone(finance_report_for_user(user,self.team,FinanceDomain.GENERAL))
        self.assertEqual(finance_report_for_user(user,self.team,FinanceDomain.IEA).income,Decimal("75.00"))

    def test_report_builds_receivable_aging_buckets(self):
        account=ReceivableAccount.objects.create(team=self.team,name="Aging Family",finance_domain=FinanceDomain.GENERAL)
        for description,amount,due in [
            ("Current","10.00",date(2026,9,30)),("15 days","20.00",date(2026,9,2)),
            ("45 days","30.00",date(2026,8,3)),("75 days","40.00",date(2026,7,4)),("Old","50.00",date(2026,5,1)),
        ]:ReceivableCharge.objects.create(account=account,description=description,amount=Decimal(amount),charge_date=due,due_date=due)
        report=finance_report_for_user(self.admin,self.team,FinanceDomain.GENERAL,as_of=date(2026,9,17))
        self.assertEqual(report.aging_buckets,{"current":Decimal("10.00"),"days_1_30":Decimal("20.00"),"days_31_60":Decimal("30.00"),"days_61_90":Decimal("40.00"),"days_90_plus":Decimal("50.00")})
    def test_report_builds_financial_account_summary(self):
        report=finance_report_for_user(self.admin,self.team,FinanceDomain.GENERAL)
        self.assertEqual(report.account_rows,({"account":"Operating","income":Decimal("500.00"),"expenses":Decimal("125.00"),"net":Decimal("375.00")},))
    def test_report_rejects_reversed_date_range(self):
        with self.assertRaises(ValueError):finance_report_for_user(self.admin,self.team,FinanceDomain.GENERAL,start_date=date(2026,9,30),end_date=date(2026,9,1))

    def test_report_can_filter_one_season(self):
        season=Season.objects.create(team=self.team,name="2026-27",start_date=date(2026,7,1),end_date=date(2027,6,30))
        FinancialTransaction.objects.create(team=self.team,season=season,transaction_date=date(2026,9,5),kind="income",account=self.general,category=self.income,amount=Decimal("225.00"),description="Season income")
        report=finance_report_for_user(self.admin,self.team,FinanceDomain.GENERAL,season=season)
        self.assertEqual(report.income,Decimal("225.00"))
        self.assertEqual(report.account_rows[0]["net"],Decimal("225.00"))
    def test_reporting_workspace_renders_authorized_report(self):
        from django.urls import reverse
        self.client.force_login(self.admin)
        response=self.client.get(reverse("finance_reporting"),{"finance_domain":FinanceDomain.GENERAL,"as_of":"2026-09-17"})
        self.assertEqual(response.status_code,200)
        self.assertContains(response,"Finance reporting")
        self.assertContains(response,"375.00")
    def test_iea_reporter_workspace_does_not_offer_general_domain(self):
        from django.urls import reverse
        user=get_user_model().objects.create_user(username="iea-ui",password="pass");p=user.profile;p.team=self.team;p.save(update_fields=["team"])
        person=Person.objects.create(team=self.team,user=user,first_name="IEA",last_name="UI")
        OrganizationCapabilityAssignment.objects.create(team=self.team,person=person,capability=OrganizationCapabilityAssignment.Capability.MANAGE_IEA_FINANCE)
        self.client.force_login(user)
        response=self.client.get(reverse("finance_reporting"))
        self.assertEqual(response.status_code,200)
        self.assertNotContains(response,'value="general"')
        self.assertContains(response,'value="iea"')
