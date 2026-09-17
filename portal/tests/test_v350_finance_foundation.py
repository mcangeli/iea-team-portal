from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from portal.models import Team
from portal.model_modules.finance import (
    ReceivableAccount,
    ReceivableAllocation,
    ReceivableCharge,
    ReceivableCredit,
    ReceivablePayment,
)


class ReceivablesFoundationTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="ArenaLine Barn")
        self.other_team = Team.objects.create(name="Other Barn")
        self.account = ReceivableAccount.objects.create(team=self.team, name="Smith Account")
        self.other_account = ReceivableAccount.objects.create(team=self.other_team, name="Jones Account")
        self.charge1 = ReceivableCharge.objects.create(
            account=self.account, description="September lessons", amount=Decimal("150.00"), charge_date=date(2026, 9, 1)
        )
        self.charge2 = ReceivableCharge.objects.create(
            account=self.account, description="October lessons", amount=Decimal("100.00"), charge_date=date(2026, 10, 1)
        )

    def test_payment_can_split_across_multiple_charges(self):
        payment = ReceivablePayment.objects.create(account=self.account, amount=Decimal("200.00"), received_date=date(2026, 9, 15))
        first = ReceivableAllocation(charge=self.charge1, payment=payment, amount=Decimal("150.00"))
        first.full_clean(); first.save()
        second = ReceivableAllocation(charge=self.charge2, payment=payment, amount=Decimal("50.00"))
        second.full_clean(); second.save()
        self.assertEqual(payment.allocated_total, Decimal("200.00"))
        self.assertEqual(payment.unapplied_amount, Decimal("0.00"))
        self.assertEqual(self.charge1.balance, Decimal("0.00"))
        self.assertEqual(self.charge2.balance, Decimal("50.00"))

    def test_payment_may_remain_unapplied(self):
        payment = ReceivablePayment.objects.create(account=self.account, amount=Decimal("75.00"), received_date=date(2026, 9, 15))
        self.assertEqual(payment.unapplied_amount, Decimal("75.00"))
        self.assertEqual(self.account.balance, Decimal("175.00"))

    def test_credit_can_be_allocated_to_charge(self):
        credit = ReceivableCredit.objects.create(
            account=self.account, description="Courtesy credit", amount=Decimal("25.00"), credit_date=date(2026, 9, 10)
        )
        allocation = ReceivableAllocation(charge=self.charge1, credit=credit, amount=Decimal("25.00"))
        allocation.full_clean(); allocation.save()
        self.assertEqual(credit.unapplied_amount, Decimal("0.00"))
        self.assertEqual(self.charge1.balance, Decimal("125.00"))
        self.assertEqual(self.account.balance, Decimal("225.00"))

    def test_allocation_rejects_cross_account_source(self):
        payment = ReceivablePayment.objects.create(account=self.other_account, amount=Decimal("25.00"), received_date=date(2026, 9, 15))
        allocation = ReceivableAllocation(charge=self.charge1, payment=payment, amount=Decimal("25.00"))
        with self.assertRaises(ValidationError):
            allocation.full_clean()

    def test_allocation_rejects_source_overallocation(self):
        payment = ReceivablePayment.objects.create(account=self.account, amount=Decimal("100.00"), received_date=date(2026, 9, 15))
        first = ReceivableAllocation(charge=self.charge1, payment=payment, amount=Decimal("80.00"))
        first.full_clean(); first.save()
        second = ReceivableAllocation(charge=self.charge2, payment=payment, amount=Decimal("30.00"))
        with self.assertRaises(ValidationError):
            second.full_clean()

    def test_allocation_rejects_charge_overallocation(self):
        payment = ReceivablePayment.objects.create(account=self.account, amount=Decimal("200.00"), received_date=date(2026, 9, 15))
        first = ReceivableAllocation(charge=self.charge2, payment=payment, amount=Decimal("90.00"))
        first.full_clean(); first.save()
        second = ReceivableAllocation(charge=self.charge2, payment=payment, amount=Decimal("20.00"))
        with self.assertRaises(ValidationError):
            second.full_clean()

    def test_void_items_do_not_affect_account_balance(self):
        ReceivablePayment.objects.create(
            account=self.account, amount=Decimal("50.00"), received_date=date(2026, 9, 15), status=ReceivablePayment.Status.VOID
        )
        ReceivableCredit.objects.create(
            account=self.account, description="Voided credit", amount=Decimal("20.00"), credit_date=date(2026, 9, 15), status=ReceivableCredit.Status.VOID
        )
        ReceivableCharge.objects.create(
            account=self.account, description="Waived charge", amount=Decimal("40.00"), charge_date=date(2026, 9, 15), status=ReceivableCharge.Status.WAIVED
        )
        self.assertEqual(self.account.balance, Decimal("250.00"))

    def test_allocation_requires_exactly_one_source(self):
        allocation = ReceivableAllocation(charge=self.charge1, amount=Decimal("10.00"))
        with self.assertRaises(ValidationError):
            allocation.full_clean()
