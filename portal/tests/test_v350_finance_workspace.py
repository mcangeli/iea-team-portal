from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.capabilities import OrganizationCapabilityAssignment
from portal.model_modules.finance import FinanceDomain, ReceivableAccount, ReceivableCharge, ReceivablePayment
from portal.model_modules.people import Person
from portal.models import Team, UserProfile


class FinanceWorkspaceTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Workspace Barn")
        self.general = ReceivableAccount.objects.create(team=self.team, name="General Account", finance_domain=FinanceDomain.GENERAL)
        self.iea = ReceivableAccount.objects.create(team=self.team, name="IEA Account", finance_domain=FinanceDomain.IEA)
        self.general_charge = ReceivableCharge.objects.create(account=self.general, description="Board", amount="125.00", charge_date=date(2026, 9, 1))
        self.iea_charge = ReceivableCharge.objects.create(account=self.iea, description="Show fee", amount="75.00", charge_date=date(2026, 9, 2))

    def _user(self, username, role=UserProfile.Role.PARENT):
        user = User.objects.create_user(username=username, password="pass12345")
        profile = user.profile
        profile.team = self.team
        profile.role = role
        profile.save(update_fields=["team", "role"])
        person = Person.objects.create(team=self.team, user=user, first_name=username, last_name="Tester")
        return user, person

    def _grant(self, person, capability):
        OrganizationCapabilityAssignment.objects.create(team=self.team, person=person, capability=capability)

    def test_admin_workspace_contains_both_domains(self):
        user, _ = self._user("admin", UserProfile.Role.ADMIN)
        self.client.force_login(user)
        response = self.client.get(reverse("finance_workspace"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "General Barn")
        self.assertContains(response, "IEA")
        self.assertContains(response, "General Account")
        self.assertContains(response, "IEA Account")

    def test_iea_treasurer_workspace_does_not_render_general_data(self):
        user, person = self._user("iea-treasurer")
        self._grant(person, OrganizationCapabilityAssignment.Capability.MANAGE_IEA_FINANCE)
        self.client.force_login(user)
        response = self.client.get(reverse("finance_workspace"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "General Account")
        self.assertContains(response, "IEA Account")

    def test_iea_treasurer_cannot_guess_general_account_detail_url(self):
        user, person = self._user("iea-detail")
        self._grant(person, OrganizationCapabilityAssignment.Capability.MANAGE_IEA_FINANCE)
        self.client.force_login(user)
        response = self.client.get(reverse("finance_receivable_account_detail", args=[self.general.pk]))
        self.assertEqual(response.status_code, 403)

    def test_iea_treasurer_cannot_guess_general_statement_url(self):
        user, person = self._user("iea-statement")
        self._grant(person, OrganizationCapabilityAssignment.Capability.MANAGE_IEA_FINANCE)
        self.client.force_login(user)
        response = self.client.get(reverse("finance_receivable_statement", args=[self.general.pk]))
        self.assertEqual(response.status_code, 403)

    def test_unprivileged_user_cannot_open_workspace(self):
        user, _ = self._user("parent")
        self.client.force_login(user)
        response = self.client.get(reverse("finance_workspace"))
        self.assertEqual(response.status_code, 403)

    def test_general_treasurer_can_open_both_account_details(self):
        user, person = self._user("general-treasurer")
        self._grant(person, OrganizationCapabilityAssignment.Capability.MANAGE_ALL_FINANCE)
        self.client.force_login(user)
        for account in (self.general, self.iea):
            response = self.client.get(reverse("finance_receivable_account_detail", args=[account.pk]))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, account.name)

    def test_statement_accepts_date_range(self):
        user, _ = self._user("statement-admin", UserProfile.Role.ADMIN)
        self.client.force_login(user)
        response = self.client.get(reverse("finance_receivable_statement", args=[self.general.pk]), {"start": "2026-09-01", "end": "2026-09-30"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sep 1, 2026")
        self.assertContains(response, "Sep 30, 2026")
        self.assertContains(response, "Board")

    def test_admin_can_post_charge_through_ui(self):
        user, _ = self._user("post-admin", UserProfile.Role.ADMIN)
        self.client.force_login(user)
        response = self.client.post(reverse("finance_charge_add", args=[self.general.pk]), {
            "description": "October board", "amount": "225.00", "charge_date": "2026-10-01", "due_date": "", "charge_type": "board", "notes": "",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.general.charges.filter(description="October board", amount="225.00").exists())

    def test_iea_treasurer_cannot_post_general_charge_by_url(self):
        user, person = self._user("post-iea")
        self._grant(person, OrganizationCapabilityAssignment.Capability.MANAGE_IEA_FINANCE)
        self.client.force_login(user)
        response = self.client.post(reverse("finance_charge_add", args=[self.general.pk]), {
            "description": "Forbidden", "amount": "50.00", "charge_date": "2026-10-01",
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(self.general.charges.filter(description="Forbidden").exists())

    def test_unprivileged_user_cannot_post_payment(self):
        user, _ = self._user("post-parent")
        self.client.force_login(user)
        response = self.client.post(reverse("finance_payment_add", args=[self.general.pk]), {
            "amount": "50.00", "received_date": "2026-10-01", "method": "check", "reference": "", "notes": "",
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(self.general.payments.exists())

    def test_payment_allocation_cannot_target_charge_on_other_account(self):
        user, _ = self._user("allocate-admin", UserProfile.Role.ADMIN)
        payment = ReceivablePayment.objects.create(account=self.general, amount="60.00", received_date=date(2026, 9, 10))
        self.client.force_login(user)
        response = self.client.post(reverse("finance_payment_allocate", args=[self.general.pk, payment.pk]), {
            "charge_id": self.iea_charge.pk, "amount": "25.00", "notes": "",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(payment.allocations.exists())

    def test_payment_id_from_other_account_cannot_be_allocated(self):
        user, _ = self._user("source-admin", UserProfile.Role.ADMIN)
        payment = ReceivablePayment.objects.create(account=self.iea, amount="60.00", received_date=date(2026, 9, 10))
        self.client.force_login(user)
        response = self.client.post(reverse("finance_payment_allocate", args=[self.general.pk, payment.pk]), {
            "charge_id": self.general_charge.pk, "amount": "25.00", "notes": "",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(payment.allocations.exists())
