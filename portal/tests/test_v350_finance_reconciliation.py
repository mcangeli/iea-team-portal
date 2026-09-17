from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from portal.model_modules.finance import FinanceDomain, ReceivableAccount, ReceivableCharge
from portal.models import Team
from portal.services.finance_receivables import (
    account_amount_due,
    account_net_balance,
    account_unapplied_credits,
    account_unapplied_payments,
    allocate_source,
    post_credit,
    post_payment,
    reconcile_legacy_account,
)


class FinanceReconciliationTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Preview 1C Barn")
        self.account = ReceivableAccount.objects.create(team=self.team, name="Smith Family", finance_domain=FinanceDomain.GENERAL)
        self.charge = ReceivableCharge.objects.create(account=self.account, description="Board", amount=Decimal("100.00"), charge_date=date(2026, 9, 1))

    def test_amount_due_tracks_allocated_charge_balance(self):
        post_payment(account=self.account, amount=Decimal("40.00"), received_date=date(2026, 9, 2), charge=self.charge)
        self.assertEqual(account_amount_due(self.account), Decimal("60.00"))
        self.assertEqual(self.account.amount_due, Decimal("60.00"))
        self.assertEqual(account_net_balance(self.account), Decimal("60.00"))
        self.assertEqual(self.account.balance, Decimal("60.00"))

    def test_overpayment_is_left_unapplied(self):
        payment = post_payment(account=self.account, amount=Decimal("125.00"), received_date=date(2026, 9, 2), charge=self.charge)
        self.assertEqual(self.charge.balance, Decimal("0.00"))
        self.assertEqual(payment.unapplied_amount, Decimal("25.00"))
        self.assertEqual(account_unapplied_payments(self.account), Decimal("25.00"))
        self.assertEqual(self.account.unapplied_payment_total, Decimal("25.00"))
        self.assertEqual(account_net_balance(self.account), Decimal("-25.00"))

    def test_overcredit_is_left_unapplied(self):
        credit = post_credit(account=self.account, description="Courtesy credit", amount=Decimal("120.00"), credit_date=date(2026, 9, 2), charge=self.charge)
        self.assertEqual(self.charge.balance, Decimal("0.00"))
        self.assertEqual(credit.unapplied_amount, Decimal("20.00"))
        self.assertEqual(account_unapplied_credits(self.account), Decimal("20.00"))
        self.assertEqual(self.account.unapplied_credit_total, Decimal("20.00"))
        self.assertEqual(account_net_balance(self.account), Decimal("-20.00"))

    def test_payment_can_be_split_across_charges_with_remainder_unapplied(self):
        second = ReceivableCharge.objects.create(account=self.account, description="Lessons", amount=Decimal("50.00"), charge_date=date(2026, 9, 3))
        payment = post_payment(account=self.account, amount=Decimal("175.00"), received_date=date(2026, 9, 4))
        allocate_source(charge=self.charge, payment=payment)
        allocate_source(charge=second, payment=payment)
        self.assertEqual(self.charge.balance, Decimal("0.00"))
        self.assertEqual(second.balance, Decimal("0.00"))
        self.assertEqual(payment.unapplied_amount, Decimal("25.00"))
        self.assertEqual(self.account.balance, Decimal("-25.00"))

    def test_void_charge_does_not_contribute_to_amount_due(self):
        self.charge.status = ReceivableCharge.Status.VOID
        self.charge.save(update_fields=["status"])
        self.assertEqual(self.account.amount_due, Decimal("0.00"))

    def test_same_name_can_exist_in_separate_finance_domains(self):
        ReceivableAccount.objects.create(team=self.team, name="Smith Family", finance_domain=FinanceDomain.IEA)
        self.assertEqual(ReceivableAccount.objects.filter(team=self.team, name="Smith Family").count(), 2)

    def test_cross_account_allocation_stays_blocked_at_service_boundary(self):
        other = ReceivableAccount.objects.create(team=self.team, name="Jones Family", finance_domain=FinanceDomain.GENERAL)
        payment = post_payment(account=other, amount=Decimal("25.00"), received_date=date(2026, 9, 2))
        with self.assertRaises(ValidationError):
            allocate_source(charge=self.charge, payment=payment)

    def test_explicit_allocation_above_available_is_capped(self):
        payment = post_payment(account=self.account, amount=Decimal("150.00"), received_date=date(2026, 9, 2))
        allocation = allocate_source(charge=self.charge, payment=payment, amount=Decimal("150.00"))
        self.assertEqual(allocation.amount, Decimal("100.00"))
        self.assertEqual(payment.unapplied_amount, Decimal("50.00"))

    def test_void_payment_is_not_counted_as_unapplied_credit(self):
        payment = post_payment(account=self.account, amount=Decimal("25.00"), received_date=date(2026, 9, 2))
        payment.status = payment.Status.VOID
        payment.save(update_fields=["status"])
        self.assertEqual(payment.unapplied_amount, Decimal("0.00"))
        self.assertEqual(self.account.balance, Decimal("100.00"))

    def test_nonlegacy_account_reconciliation_reports_current_amount_due(self):
        result = reconcile_legacy_account(self.account)
        self.assertEqual(result["legacy_amount_due"], Decimal("0.00"))
        self.assertEqual(result["receivable_amount_due"], Decimal("100.00"))
        self.assertEqual(result["difference"], Decimal("100.00"))
