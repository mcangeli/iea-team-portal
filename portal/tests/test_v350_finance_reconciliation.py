from datetime import date
from decimal import Decimal

from django.test import TestCase

from portal.model_modules.finance import FinanceDomain, ReceivableAccount, ReceivableCharge
from portal.models import Team
from portal.services.finance_receivables import (
    account_amount_due,
    account_net_balance,
    account_unapplied_credits,
    account_unapplied_payments,
    post_credit,
    post_payment,
)


class FinanceReconciliationTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Preview 1C Barn")
        self.account = ReceivableAccount.objects.create(
            team=self.team,
            name="Smith Family",
            finance_domain=FinanceDomain.GENERAL,
        )
        self.charge = ReceivableCharge.objects.create(
            account=self.account,
            description="Board",
            amount=Decimal("100.00"),
            charge_date=date(2026, 9, 1),
        )

    def test_amount_due_tracks_allocated_charge_balance(self):
        post_payment(
            account=self.account,
            amount=Decimal("40.00"),
            received_date=date(2026, 9, 2),
            charge=self.charge,
        )
        self.assertEqual(account_amount_due(self.account), Decimal("60.00"))
        self.assertEqual(account_net_balance(self.account), Decimal("60.00"))

    def test_overpayment_is_left_unapplied(self):
        payment = post_payment(
            account=self.account,
            amount=Decimal("125.00"),
            received_date=date(2026, 9, 2),
            charge=self.charge,
        )
        self.assertEqual(self.charge.balance, Decimal("0.00"))
        self.assertEqual(payment.unapplied_amount, Decimal("25.00"))
        self.assertEqual(account_amount_due(self.account), Decimal("0.00"))
        self.assertEqual(account_unapplied_payments(self.account), Decimal("25.00"))
        self.assertEqual(account_net_balance(self.account), Decimal("-25.00"))

    def test_overcredit_is_left_unapplied(self):
        credit = post_credit(
            account=self.account,
            description="Courtesy credit",
            amount=Decimal("120.00"),
            credit_date=date(2026, 9, 2),
            charge=self.charge,
        )
        self.assertEqual(self.charge.balance, Decimal("0.00"))
        self.assertEqual(credit.unapplied_amount, Decimal("20.00"))
        self.assertEqual(account_unapplied_credits(self.account), Decimal("20.00"))
        self.assertEqual(account_net_balance(self.account), Decimal("-20.00"))

    def test_same_name_can_exist_in_separate_finance_domains(self):
        ReceivableAccount.objects.create(
            team=self.team,
            name="Smith Family",
            finance_domain=FinanceDomain.IEA,
        )
        self.assertEqual(
            ReceivableAccount.objects.filter(team=self.team, name="Smith Family").count(),
            2,
        )
