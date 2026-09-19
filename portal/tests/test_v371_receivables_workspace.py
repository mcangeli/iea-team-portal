from datetime import date
from decimal import Decimal
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from portal.model_modules.capabilities import OrganizationCapabilityAssignment
from portal.model_modules.finance import FinanceDomain, ReceivableAccount, ReceivableCharge
from portal.model_modules.people import Person
from portal.models import Team, UserProfile
from portal.services.finance_receivable_reports import receivable_workspace_summary

class ReceivablesWorkspaceTests(TestCase):
    def setUp(self):
        self.team=Team.objects.create(name="AR Workspace Barn")
        self.user=User.objects.create_user(username="ar-admin",password="pass12345")
        p=self.user.profile;p.team=self.team;p.role=UserProfile.Role.ADMIN;p.save(update_fields=["team","role"])
        self.general=ReceivableAccount.objects.create(team=self.team,name="Boarding Customer",finance_domain=FinanceDomain.GENERAL)
        self.iea=ReceivableAccount.objects.create(team=self.team,name="IEA Family",finance_domain=FinanceDomain.IEA)
        ReceivableCharge.objects.create(account=self.general,description="September board",amount=Decimal("600.00"),charge_date=date(2026,9,1),due_date=date(2026,9,10))
        self.client.force_login(self.user)

    def test_summary_reports_open_and_overdue_balances(self):
        summary=receivable_workspace_summary(self.user,self.team,finance_domain=FinanceDomain.GENERAL,as_of=date(2026,9,19))
        self.assertEqual(summary["open_total"],Decimal("600.00"))
        self.assertEqual(summary["overdue_total"],Decimal("600.00"))
        self.assertEqual(summary["account_count"],1)

    def test_admin_receivables_workspace_renders_general_domain(self):
        response=self.client.get(reverse("finance_receivables"))
        self.assertEqual(response.status_code,200)
        self.assertContains(response,"Boarding Customer")
        self.assertNotContains(response,"IEA Family")

    def test_iea_only_user_cannot_view_general_receivables(self):
        user=User.objects.create_user(username="ar-iea",password="pass12345")
        p=user.profile;p.team=self.team;p.role=UserProfile.Role.PARENT;p.save(update_fields=["team","role"])
        person=Person.objects.create(team=self.team,user=user,first_name="IEA",last_name="Finance")
        OrganizationCapabilityAssignment.objects.create(team=self.team,person=person,capability=OrganizationCapabilityAssignment.Capability.MANAGE_IEA_FINANCE)
        self.client.force_login(user)
        response=self.client.get(reverse("finance_receivables")+"?domain=general")
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.context["selected_domain"],FinanceDomain.IEA)
        self.assertContains(response,"IEA Family")
        self.assertNotContains(response,"Boarding Customer")
