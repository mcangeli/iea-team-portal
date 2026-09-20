from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from portal.model_modules.finance import FinanceDomain, PayableObligation, PayableParty, PayablePayment
from portal.models import FinancialAccount, FinancialCategory, Team, UserProfile
from portal.services.finance_payable_reports import payable_workspace_summary


class PayableLifecycleTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Lifecycle Barn")
        self.user = User.objects.create_user(username="ap-admin", password="pass12345")
        profile = self.user.profile
        profile.team = self.team
        profile.role = UserProfile.Role.ADMIN
        profile.save(update_fields=["team", "role"])
        self.category = FinancialCategory.objects.create(team=self.team, name="Supplies", kind=FinancialCategory.Kind.EXPENSE)
        self.bank = FinancialAccount.objects.create(team=self.team, name="Checking", finance_domain=FinanceDomain.GENERAL)
        self.party = PayableParty.objects.create(team=self.team, name="Vendor", finance_domain=FinanceDomain.GENERAL)

    def bill(self, description, amount, due_date):
        return PayableObligation.objects.create(
            party=self.party, expense_category=self.category, description=description,
            amount=amount, obligation_date=date(2026, 9, 1), due_date=due_date,
        )

    def test_lifecycle_states_are_derived(self):
        overdue = self.bill("Overdue", Decimal("100"), date(2026, 9, 10))
        due = self.bill("Due today", Decimal("200"), date(2026, 9, 19))
        future = self.bill("Future", Decimal("300"), date(2026, 9, 25))
        self.assertEqual(overdue.lifecycle_status(date(2026, 9, 19)), "overdue")
        self.assertEqual(due.lifecycle_status(date(2026, 9, 19)), "due")
        self.assertEqual(future.lifecycle_status(date(2026, 9, 19)), "open")

    def test_paid_and_void_states_take_precedence(self):
        paid = self.bill("Paid", Decimal("100"), date(2026, 9, 1))
        PayablePayment.objects.create(obligation=paid, amount=Decimal("100"), paid_date=date(2026, 9, 5), payment_account=self.bank)
        void = self.bill("Void", Decimal("100"), date(2026, 9, 1))
        void.status = PayableObligation.Status.VOID
        void.save(update_fields=["status"])
        self.assertEqual(paid.lifecycle_status(date(2026, 9, 19)), "paid")
        self.assertEqual(void.lifecycle_status(date(2026, 9, 19)), "void")

    def test_workspace_summary_uses_outstanding_balances(self):
        overdue = self.bill("Overdue", Decimal("100"), date(2026, 9, 10))
        PayablePayment.objects.create(obligation=overdue, amount=Decimal("25"), paid_date=date(2026, 9, 11), payment_account=self.bank)
        self.bill("Due", Decimal("200"), date(2026, 9, 19))
        self.bill("Open", Decimal("300"), date(2026, 9, 25))
        summary = payable_workspace_summary(self.user, self.team, as_of=date(2026, 9, 19))
        self.assertEqual(summary["open_total"], Decimal("575"))
        self.assertEqual(summary["overdue_total"], Decimal("75"))
        self.assertEqual(summary["due_total"], Decimal("200"))
        self.assertEqual(len(summary["rows"]), 3)
