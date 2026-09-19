from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.test import TestCase

from portal.model_modules.capabilities import OrganizationCapabilityAssignment
from portal.model_modules.finance import FinanceDomain, PayableObligation
from portal.model_modules.people import Person
from portal.models import FinancialAccount, FinancialCategory, FinancialTransaction, Team, UserProfile
from portal.services.finance_access import payable_parties_for_user
from portal.services.finance_payable_operations import (
    create_payable_obligation_for_user,
    create_payable_party_for_user,
    post_payable_payment_for_user,
    void_payable_payment_for_user,
)


class AccountsPayableOperationsTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="AP Barn")
        self.expense = FinancialCategory.objects.create(team=self.team, name="Feed", kind=FinancialCategory.Kind.EXPENSE)
        self.bank = FinancialAccount.objects.create(team=self.team, name="Checking", finance_domain=FinanceDomain.GENERAL)

    def _user(self, username, capability=None, role=UserProfile.Role.PARENT):
        user = User.objects.create_user(username=username, password="pass12345")
        profile = user.profile
        profile.team = self.team
        profile.role = role
        profile.save(update_fields=["team", "role"])
        person = Person.objects.create(team=self.team, user=user, first_name=username, last_name="Tester")
        if capability:
            OrganizationCapabilityAssignment.objects.create(team=self.team, person=person, capability=capability)
        return user

    def test_admin_payment_creates_existing_expense_ledger_transaction(self):
        user = self._user("admin", role=UserProfile.Role.ADMIN)
        party = create_payable_party_for_user(user, team=self.team, name="Hay Supplier", finance_domain=FinanceDomain.GENERAL)
        bill = create_payable_obligation_for_user(
            user, party.pk, expense_category=self.expense, description="September hay",
            amount="500.00", obligation_date=date(2026, 9, 1), team=self.team,
        )
        payment = post_payable_payment_for_user(
            user, bill.pk, amount="200.00", paid_date=date(2026, 9, 10),
            payment_account=self.bank, reference="CHK-200", team=self.team,
        )
        tx = payment.financial_transaction
        self.assertIsNotNone(tx)
        self.assertEqual(tx.kind, FinancialTransaction.Kind.EXPENSE)
        self.assertEqual(tx.amount, Decimal("200.00"))
        self.assertEqual(tx.account, self.bank)
        self.assertEqual(tx.category, self.expense)
        self.assertEqual(tx.payee, party.name)
        self.assertEqual(bill.balance, Decimal("300.00"))

    def test_void_payment_restores_balance_and_voids_ledger_transaction(self):
        user = self._user("void-admin", role=UserProfile.Role.ADMIN)
        party = create_payable_party_for_user(user, team=self.team, name="Farrier", finance_domain=FinanceDomain.GENERAL)
        bill = create_payable_obligation_for_user(
            user, party.pk, expense_category=self.expense, description="Farrier",
            amount="150.00", obligation_date=date(2026, 9, 1), team=self.team,
        )
        payment = post_payable_payment_for_user(
            user, bill.pk, amount="150.00", paid_date=date(2026, 9, 10),
            payment_account=self.bank, team=self.team,
        )
        tx_id = payment.financial_transaction_id
        void_payable_payment_for_user(user, bill.pk, payment_id=payment.pk, reason="Duplicate", team=self.team)
        payment.refresh_from_db()
        bill.refresh_from_db()
        tx = FinancialTransaction.objects.get(pk=tx_id)
        self.assertEqual(payment.status, payment.Status.VOID)
        self.assertEqual(tx.status, FinancialTransaction.Status.VOID)
        self.assertEqual(tx.void_reason, "Duplicate")
        self.assertEqual(bill.balance, Decimal("150.00"))

    def test_iea_finance_manager_cannot_create_general_payee(self):
        user = self._user("iea", OrganizationCapabilityAssignment.Capability.MANAGE_IEA_FINANCE)
        with self.assertRaises(PermissionDenied):
            create_payable_party_for_user(user, team=self.team, name="General Vendor", finance_domain=FinanceDomain.GENERAL)

    def test_iea_finance_manager_only_sees_iea_payees(self):
        admin = self._user("seed-admin", role=UserProfile.Role.ADMIN)
        general = create_payable_party_for_user(admin, team=self.team, name="General Vendor", finance_domain=FinanceDomain.GENERAL)
        iea = create_payable_party_for_user(admin, team=self.team, name="IEA Vendor", finance_domain=FinanceDomain.IEA)
        user = self._user("iea-view", OrganizationCapabilityAssignment.Capability.MANAGE_IEA_FINANCE)
        visible = payable_parties_for_user(user, self.team)
        self.assertNotIn(general, visible)
        self.assertIn(iea, visible)

    def test_general_finance_manager_can_manage_both_domains(self):
        user = self._user("finance", OrganizationCapabilityAssignment.Capability.MANAGE_ALL_FINANCE)
        general = create_payable_party_for_user(user, team=self.team, name="General Vendor", finance_domain=FinanceDomain.GENERAL)
        iea = create_payable_party_for_user(user, team=self.team, name="IEA Vendor", finance_domain=FinanceDomain.IEA)
        self.assertEqual(set(payable_parties_for_user(user, self.team)), {general, iea})
