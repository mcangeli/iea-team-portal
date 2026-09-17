from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from portal.models import FinancialAccount, Team
from portal.model_modules.finance import (
    FinanceDomain,
    ReceivableAccount,
    ReceivableAllocation,
    ReceivableCharge,
    ReceivablePayment,
)


class FinanceDomainBoundaryTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="ArenaLine Barn")
        self.general_account = ReceivableAccount.objects.create(
            team=self.team, name="Smith General", finance_domain=FinanceDomain.GENERAL
        )
        self.iea_account = ReceivableAccount.objects.create(
            team=self.team, name="Smith IEA", finance_domain=FinanceDomain.IEA
        )
        self.general_bank = FinancialAccount.objects.create(
            team=self.team,
            name="Barn Checking",
            finance_domain=FinanceDomain.GENERAL,
        )
        self.iea_bank = FinancialAccount.objects.create(
            team=self.team,
            name="IEA Checking",
            finance_domain=FinanceDomain.IEA,
        )

    def test_domains_are_explicit_and_distinct(self):
        self.assertEqual(FinanceDomain.GENERAL, "general")
        self.assertEqual(FinanceDomain.IEA, "iea")
        self.assertNotEqual(FinanceDomain.GENERAL, FinanceDomain.IEA)

    def test_payment_rejects_deposit_account_from_other_domain(self):
        payment = ReceivablePayment(
            account=self.iea_account,
            amount=Decimal("75.00"),
            received_date=date(2026, 9, 17),
            deposit_account=self.general_bank,
        )
        with self.assertRaises(ValidationError):
            payment.full_clean()

    def test_payment_accepts_deposit_account_from_same_domain(self):
        payment = ReceivablePayment(
            account=self.iea_account,
            amount=Decimal("75.00"),
            received_date=date(2026, 9, 17),
            deposit_account=self.iea_bank,
        )
        payment.full_clean()

    def test_cross_domain_allocation_is_impossible_via_account_boundary(self):
        charge = ReceivableCharge.objects.create(
            account=self.general_account,
            description="Lesson package",
            amount=Decimal("100.00"),
            charge_date=date(2026, 9, 17),
        )
        payment = ReceivablePayment.objects.create(
            account=self.iea_account,
            amount=Decimal("100.00"),
            received_date=date(2026, 9, 17),
        )
        allocation = ReceivableAllocation(charge=charge, payment=payment, amount=Decimal("100.00"))
        with self.assertRaises(ValidationError):
            allocation.full_clean()
