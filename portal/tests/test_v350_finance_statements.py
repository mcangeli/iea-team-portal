from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from portal.model_modules.capabilities import OrganizationCapabilityAssignment
from portal.model_modules.finance import FinanceDomain, ReceivableAccount, ReceivableCharge, ReceivableCredit, ReceivablePayment
from portal.model_modules.people import Person
from portal.models import Team, UserProfile
from portal.services.finance_statements import account_activity, statement_for_account, statement_for_user


class FinanceStatementTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Statement Barn")
        self.general = ReceivableAccount.objects.create(team=self.team, name="Smith Family", finance_domain=FinanceDomain.GENERAL)
        self.iea = ReceivableAccount.objects.create(team=self.team, name="Smith Family", finance_domain=FinanceDomain.IEA)

    def _user(self, username, role=UserProfile.Role.PARENT):
        user = User.objects.create_user(username=username, password="pass12345")
        profile = user.profile
        profile.team = self.team
        profile.role = role
        profile.save(update_fields=["team", "role"])
        person = Person.objects.create(team=self.team, user=user, first_name=username, last_name="Tester")
        return user, person

    def _seed_general(self):
        ReceivableCharge.objects.create(account=self.general, description="August board", amount="100.00", charge_date=date(2026, 8, 15))
        ReceivablePayment.objects.create(account=self.general, amount="25.00", received_date=date(2026, 8, 20), reference="ACH 100")
        ReceivableCharge.objects.create(account=self.general, description="September board", amount="80.00", charge_date=date(2026, 9, 1))
        ReceivableCredit.objects.create(account=self.general, description="Lesson adjustment", amount="10.00", credit_date=date(2026, 9, 5))
        ReceivablePayment.objects.create(account=self.general, amount="40.00", received_date=date(2026, 9, 10), reference="Check 42")

    def test_activity_is_chronological_with_running_net_balance(self):
        self._seed_general()
        rows = account_activity(self.general)
        self.assertEqual([row.kind for row in rows], ["charge", "payment", "charge", "credit", "payment"])
        self.assertEqual([row.balance for row in rows], [Decimal("100.00"), Decimal("75.00"), Decimal("155.00"), Decimal("145.00"), Decimal("105.00")])

    def test_statement_has_opening_and_closing_balance(self):
        self._seed_general()
        statement = statement_for_account(self.general, start_date=date(2026, 9, 1), end_date=date(2026, 9, 30))
        self.assertEqual(statement.opening_balance, Decimal("75.00"))
        self.assertEqual(statement.charges, Decimal("80.00"))
        self.assertEqual(statement.credits, Decimal("10.00"))
        self.assertEqual(statement.payments, Decimal("40.00"))
        self.assertEqual(statement.closing_balance, Decimal("105.00"))
        self.assertEqual(len(statement.activity), 3)

    def test_void_rows_do_not_appear_or_change_statement(self):
        ReceivableCharge.objects.create(account=self.general, description="Void charge", amount="100.00", charge_date=date(2026, 9, 1), status=ReceivableCharge.Status.VOID)
        ReceivablePayment.objects.create(account=self.general, amount="20.00", received_date=date(2026, 9, 2), status=ReceivablePayment.Status.VOID)
        statement = statement_for_account(self.general, start_date=date(2026, 9, 1), end_date=date(2026, 9, 30))
        self.assertEqual(statement.closing_balance, Decimal("0.00"))
        self.assertEqual(statement.activity, ())

    def test_empty_period_carries_opening_balance_forward(self):
        ReceivableCharge.objects.create(account=self.general, description="Old charge", amount="55.00", charge_date=date(2026, 8, 1))
        statement = statement_for_account(self.general, start_date=date(2026, 9, 1), end_date=date(2026, 9, 30))
        self.assertEqual(statement.opening_balance, Decimal("55.00"))
        self.assertEqual(statement.closing_balance, Decimal("55.00"))

    def test_invalid_statement_period_is_rejected(self):
        with self.assertRaises(ValueError):
            statement_for_account(self.general, start_date=date(2026, 9, 30), end_date=date(2026, 9, 1))

    def test_iea_treasurer_cannot_generate_general_statement_by_id(self):
        self._seed_general()
        user, person = self._user("iea-statement")
        OrganizationCapabilityAssignment.objects.create(team=self.team, person=person, capability=OrganizationCapabilityAssignment.Capability.MANAGE_IEA_FINANCE)
        self.assertIsNone(statement_for_user(user, self.general.pk, start_date=date(2026, 9, 1), end_date=date(2026, 9, 30), team=self.team))

    def test_iea_treasurer_can_generate_iea_statement(self):
        ReceivableCharge.objects.create(account=self.iea, description="Show fee", amount="75.00", charge_date=date(2026, 9, 1))
        user, person = self._user("iea-statement-ok")
        OrganizationCapabilityAssignment.objects.create(team=self.team, person=person, capability=OrganizationCapabilityAssignment.Capability.MANAGE_IEA_FINANCE)
        statement = statement_for_user(user, self.iea.pk, start_date=date(2026, 9, 1), end_date=date(2026, 9, 30), team=self.team)
        self.assertIsNotNone(statement)
        self.assertEqual(statement.closing_balance, Decimal("75.00"))

    def test_general_treasurer_can_generate_both_domain_statements(self):
        ReceivableCharge.objects.create(account=self.general, description="Board", amount="100.00", charge_date=date(2026, 9, 1))
        ReceivableCharge.objects.create(account=self.iea, description="Show fee", amount="75.00", charge_date=date(2026, 9, 1))
        user, person = self._user("general-statement")
        OrganizationCapabilityAssignment.objects.create(team=self.team, person=person, capability=OrganizationCapabilityAssignment.Capability.MANAGE_ALL_FINANCE)
        general = statement_for_user(user, self.general.pk, start_date=date(2026, 9, 1), end_date=date(2026, 9, 30), team=self.team)
        iea = statement_for_user(user, self.iea.pk, start_date=date(2026, 9, 1), end_date=date(2026, 9, 30), team=self.team)
        self.assertEqual(general.closing_balance, Decimal("100.00"))
        self.assertEqual(iea.closing_balance, Decimal("75.00"))
