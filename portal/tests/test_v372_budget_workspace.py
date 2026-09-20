from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.capabilities import OrganizationCapabilityAssignment
from portal.model_modules.finance import Budget, BudgetLine, FinanceDomain
from portal.model_modules.people import Person
from portal.models import FinancialAccount, FinancialCategory, FinancialTransaction, Team, UserProfile


class V372BudgetWorkspaceTests(TestCase):
    def setUp(self):
        self.team=Team.objects.create(name="Workspace Barn")
        self.expense=FinancialCategory.objects.create(team=self.team,name="Hay",kind=FinancialCategory.Kind.EXPENSE)
        self.income=FinancialCategory.objects.create(team=self.team,name="Board",kind=FinancialCategory.Kind.INCOME)
        self.bank=FinancialAccount.objects.create(team=self.team,name="Checking",finance_domain=FinanceDomain.GENERAL)
        self.admin=User.objects.create_user(username="budget-admin",password="pass12345")
        profile=self.admin.profile;profile.team=self.team;profile.role=UserProfile.Role.ADMIN;profile.save(update_fields=["team","role"])

    def test_admin_can_create_general_budget(self):
        self.client.force_login(self.admin)
        response=self.client.post(reverse("finance_budget_add")+"?domain=general",{"finance_domain":"general","name":"2027 Barn Budget","start_date":"2027-01-01","end_date":"2027-12-31","status":"active","notes":""})
        budget=Budget.objects.get(name="2027 Barn Budget")
        self.assertRedirects(response,reverse("finance_budget_detail",args=[budget.pk]))
        self.assertEqual(budget.finance_domain,FinanceDomain.GENERAL)

    def test_admin_can_add_budget_line_and_detail_shows_actual(self):
        budget=Budget.objects.create(team=self.team,finance_domain=FinanceDomain.GENERAL,name="Operating",start_date=date(2027,1,1),end_date=date(2027,12,31),status=Budget.Status.ACTIVE)
        self.client.force_login(self.admin)
        response=self.client.post(reverse("finance_budget_line_add",args=[budget.pk]),{"kind":"expense","category":self.expense.pk,"description":"Hay and forage","amount":"12000.00","sort_order":"10","notes":""})
        self.assertRedirects(response,reverse("finance_budget_detail",args=[budget.pk]))
        FinancialTransaction.objects.create(team=self.team,transaction_date=date(2027,2,1),kind=FinancialTransaction.Kind.EXPENSE,account=self.bank,category=self.expense,amount=Decimal("3000.00"),description="Hay")
        response=self.client.get(reverse("finance_budget_detail",args=[budget.pk]))
        self.assertContains(response,"Hay and forage");self.assertContains(response,"3000.00");self.assertContains(response,"25.0%")

    def test_iea_only_finance_user_cannot_open_general_budget(self):
        budget=Budget.objects.create(team=self.team,finance_domain=FinanceDomain.GENERAL,name="Private General",start_date=date(2027,1,1),end_date=date(2027,12,31))
        user=User.objects.create_user(username="iea-budget",password="pass12345")
        profile=user.profile;profile.team=self.team;profile.role=UserProfile.Role.PARENT;profile.save(update_fields=["team","role"])
        person=Person.objects.create(team=self.team,user=user,first_name="IEA",last_name="Treasurer")
        OrganizationCapabilityAssignment.objects.create(team=self.team,person=person,capability=OrganizationCapabilityAssignment.Capability.MANAGE_IEA_FINANCE)
        self.client.force_login(user)
        response=self.client.get(reverse("finance_budget_detail",args=[budget.pk]))
        self.assertEqual(response.status_code,403)

    def test_finance_workspace_links_budgets(self):
        self.client.force_login(self.admin)
        response=self.client.get(reverse("finance_workspace"))
        self.assertContains(response,reverse("finance_budgets"))
