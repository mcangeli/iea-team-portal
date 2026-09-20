from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.capabilities import OrganizationCapabilityAssignment
from portal.model_modules.finance import Budget, BudgetLine, FinanceDomain, PayableObligation, PayableParty, ReceivableAccount, ReceivableCharge
from portal.model_modules.people import Person
from portal.models import FinancialAccount, FinancialCategory, FinancialTransaction, Team, UserProfile


class FinanceWorkspaceRenderTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Finance UI Barn")

    def _user(self, username, role=UserProfile.Role.PARENT):
        user = User.objects.create_user(username=username, password="pass12345")
        profile = user.profile
        profile.team = self.team
        profile.role = role
        profile.save(update_fields=["team", "role"])
        person = Person.objects.create(
            team=self.team,
            user=user,
            first_name=username,
            last_name="Tester",
        )
        return user, person

    def test_admin_finance_workspace_renders_and_links_payables(self):
        user, _ = self._user("finance-ui-admin", UserProfile.Role.ADMIN)
        self.client.force_login(user)

        response = self.client.get(reverse("finance_workspace"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "portal/finance_workspace_v350.html")
        self.assertContains(response, reverse("finance_payables"))

    def test_admin_payables_workspace_renders(self):
        user, _ = self._user("payables-ui-admin", UserProfile.Role.ADMIN)
        self.client.force_login(user)

        response = self.client.get(reverse("finance_payables"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "portal/finance_payables_v370.html")
        self.assertEqual(response.context["selected_domain"], FinanceDomain.GENERAL)
        self.assertContains(response, "Payables")

    def test_iea_only_finance_user_renders_iea_payables(self):
        user, person = self._user("payables-ui-iea")
        OrganizationCapabilityAssignment.objects.create(
            team=self.team,
            person=person,
            capability=OrganizationCapabilityAssignment.Capability.MANAGE_IEA_FINANCE,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("finance_payables"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_domain"], FinanceDomain.IEA)
        self.assertNotContains(response, "domain=general")

    def test_unprivileged_user_cannot_open_finance_workspaces(self):
        user, _ = self._user("finance-ui-parent")
        self.client.force_login(user)

        self.assertEqual(self.client.get(reverse("finance_workspace")).status_code, 403)
        self.assertEqual(self.client.get(reverse("finance_payables")).status_code, 403)


    def test_workspace_dashboard_summarizes_ar_ap_budget_and_activity(self):
        user, _ = self._user("finance-dashboard-admin", UserProfile.Role.ADMIN)
        income=FinancialCategory.objects.create(team=self.team,name="Board",kind=FinancialCategory.Kind.INCOME)
        expense=FinancialCategory.objects.create(team=self.team,name="Hay",kind=FinancialCategory.Kind.EXPENSE)
        bank=FinancialAccount.objects.create(team=self.team,name="Operating",finance_domain=FinanceDomain.GENERAL)
        account=ReceivableAccount.objects.create(team=self.team,name="Boarder",finance_domain=FinanceDomain.GENERAL)
        ReceivableCharge.objects.create(account=account,description="Past due board",amount=Decimal("150.00"),charge_date=date(2026,8,1),due_date=date(2026,8,15))
        vendor=PayableParty.objects.create(team=self.team,name="Hay Vendor",finance_domain=FinanceDomain.GENERAL)
        PayableObligation.objects.create(party=vendor,expense_category=expense,description="Past due hay",amount=Decimal("80.00"),obligation_date=date(2026,8,1),due_date=date(2026,8,15))
        budget=Budget.objects.create(team=self.team,finance_domain=FinanceDomain.GENERAL,name="Operating Plan",start_date=date(2026,1,1),end_date=date(2026,12,31),status=Budget.Status.ACTIVE)
        BudgetLine.objects.create(budget=budget,category=expense,kind=FinancialTransaction.Kind.EXPENSE,description="Hay",amount=Decimal("50.00"))
        FinancialTransaction.objects.create(team=self.team,transaction_date=date(2026,9,1),kind=FinancialTransaction.Kind.EXPENSE,account=bank,category=expense,amount=Decimal("75.00"),description="Hay purchase")
        self.client.force_login(user)
        response=self.client.get(reverse("finance_workspace"))
        self.assertEqual(response.status_code,200)
        general=next(row for row in response.context["domain_summaries"] if row["domain"]==FinanceDomain.GENERAL)
        self.assertEqual(general["receivables"]["overdue_total"],Decimal("150.00"))
        self.assertEqual(general["payables"]["overdue_total"],Decimal("80.00"))
        self.assertEqual(len(general["budgets"]),1)
        self.assertTrue(any(item["kind"]=="Budget" for item in general["exceptions"]))
        self.assertContains(response,"Hay purchase")

    def test_iea_only_dashboard_does_not_expose_general_domain(self):
        user, person = self._user("finance-dashboard-iea")
        OrganizationCapabilityAssignment.objects.create(team=self.team,person=person,capability=OrganizationCapabilityAssignment.Capability.MANAGE_IEA_FINANCE)
        self.client.force_login(user)
        response=self.client.get(reverse("finance_workspace"))
        self.assertEqual(response.status_code,200)
        self.assertEqual([row["domain"] for row in response.context["domain_summaries"]],[FinanceDomain.IEA])
        self.assertNotContains(response,"General Barn finance")
