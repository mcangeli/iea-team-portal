from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from portal.model_modules.finance import (
    FinanceDomain,
    PayableObligation,
    PayableParty,
    PayablePayment,
)
from portal.models import FinancialAccount, FinancialCategory, FinancialTransaction, Team


class AccountsPayableFoundationTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="ArenaLine Barn")
        self.other_team = Team.objects.create(name="Other Barn")
        self.category = FinancialCategory.objects.create(
            team=self.team, name="Feed", kind=FinancialCategory.Kind.EXPENSE
        )
        self.party = PayableParty.objects.create(
            team=self.team, name="Hay Supplier", finance_domain=FinanceDomain.GENERAL
        )
        self.obligation = PayableObligation.objects.create(
            party=self.party,
            expense_category=self.category,
            description="September hay",
            amount=Decimal("500.00"),
            obligation_date=date(2026, 9, 1),
            due_date=date(2026, 9, 30),
        )
        self.bank = FinancialAccount.objects.create(
            team=self.team, name="General Checking", finance_domain=FinanceDomain.GENERAL
        )

    def test_obligation_tracks_partial_and_full_payment_balance(self):
        first = PayablePayment(
            obligation=self.obligation,
            amount=Decimal("200.00"),
            paid_date=date(2026, 9, 10),
            payment_account=self.bank,
        )
        first.full_clean()
        first.save()
        self.assertEqual(self.obligation.paid_total, Decimal("200.00"))
        self.assertEqual(self.obligation.balance, Decimal("300.00"))
        self.assertFalse(self.obligation.is_paid)

        second = PayablePayment(
            obligation=self.obligation,
            amount=Decimal("300.00"),
            paid_date=date(2026, 9, 20),
            payment_account=self.bank,
        )
        second.full_clean()
        second.save()
        self.assertEqual(self.obligation.balance, Decimal("0.00"))
        self.assertTrue(self.obligation.is_paid)

    def test_payment_cannot_exceed_outstanding_obligation(self):
        payment = PayablePayment(
            obligation=self.obligation,
            amount=Decimal("501.00"),
            paid_date=date(2026, 9, 10),
            payment_account=self.bank,
        )
        with self.assertRaises(ValidationError):
            payment.full_clean()

    def test_payment_account_must_match_finance_domain(self):
        iea_bank = FinancialAccount.objects.create(
            team=self.team, name="IEA Checking", finance_domain=FinanceDomain.IEA
        )
        payment = PayablePayment(
            obligation=self.obligation,
            amount=Decimal("100.00"),
            paid_date=date(2026, 9, 10),
            payment_account=iea_bank,
        )
        with self.assertRaises(ValidationError):
            payment.full_clean()

    def test_expense_category_must_belong_to_same_organization(self):
        other_category = FinancialCategory.objects.create(
            team=self.other_team, name="Feed", kind=FinancialCategory.Kind.EXPENSE
        )
        obligation = PayableObligation(
            party=self.party,
            expense_category=other_category,
            description="Invalid cross-org bill",
            amount=Decimal("100.00"),
            obligation_date=date(2026, 9, 1),
        )
        with self.assertRaises(ValidationError):
            obligation.full_clean()

    def test_payable_requires_expense_capable_category(self):
        income = FinancialCategory.objects.create(
            team=self.team, name="Lesson Income", kind=FinancialCategory.Kind.INCOME
        )
        obligation = PayableObligation(
            party=self.party,
            expense_category=income,
            description="Invalid income category",
            amount=Decimal("100.00"),
            obligation_date=date(2026, 9, 1),
        )
        with self.assertRaises(ValidationError):
            obligation.full_clean()

    def test_void_obligation_has_zero_balance(self):
        self.obligation.status = PayableObligation.Status.VOID
        self.obligation.save(update_fields=["status"])
        self.assertEqual(self.obligation.balance, Decimal("0.00"))
        self.assertFalse(self.obligation.is_paid)

    def test_void_payment_does_not_reduce_balance(self):
        PayablePayment.objects.create(
            obligation=self.obligation,
            amount=Decimal("100.00"),
            paid_date=date(2026, 9, 10),
            payment_account=self.bank,
            status=PayablePayment.Status.VOID,
        )
        self.assertEqual(self.obligation.balance, Decimal("500.00"))

    def test_linked_ledger_transaction_must_be_expense(self):
        income_category = FinancialCategory.objects.create(
            team=self.team, name="Income", kind=FinancialCategory.Kind.INCOME
        )
        tx = FinancialTransaction.objects.create(
            team=self.team,
            transaction_date=date(2026, 9, 10),
            kind=FinancialTransaction.Kind.INCOME,
            account=self.bank,
            category=income_category,
            amount=Decimal("100.00"),
            description="Wrong transaction type",
        )
        payment = PayablePayment(
            obligation=self.obligation,
            amount=Decimal("100.00"),
            paid_date=date(2026, 9, 10),
            payment_account=self.bank,
            financial_transaction=tx,
        )
        with self.assertRaises(ValidationError):
            payment.full_clean()

    def test_same_payee_name_may_exist_in_separate_finance_domains(self):
        iea_party = PayableParty.objects.create(
            team=self.team, name="Hay Supplier", finance_domain=FinanceDomain.IEA
        )
        self.assertNotEqual(self.party.pk, iea_party.pk)
