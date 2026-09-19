from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.finance import FinanceDomain, PayableObligation, PayableParty, PayablePayment
from portal.models import FinancialAccount, FinancialCategory, FinancialTransaction, Team, UserProfile


class PayableWriteUITests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="AP Write UI Barn")
        self.user = User.objects.create_user(username="ap-ui-admin", password="pass12345")
        profile = self.user.profile
        profile.team = self.team
        profile.role = UserProfile.Role.ADMIN
        profile.save(update_fields=["team", "role"])
        self.category = FinancialCategory.objects.create(team=self.team, name="Feed", kind=FinancialCategory.Kind.EXPENSE)
        self.bank = FinancialAccount.objects.create(team=self.team, name="Operating Checking", finance_domain=FinanceDomain.GENERAL)
        self.client.force_login(self.user)

    def test_create_payee_post(self):
        response = self.client.post(reverse("finance_payable_party_add"), {
            "name": "Hay Supplier",
            "finance_domain": FinanceDomain.GENERAL,
            "party_type": PayableParty.PartyType.VENDOR,
            "email": "billing@example.com",
            "phone": "",
            "notes": "",
        })
        self.assertEqual(response.status_code, 302)
        party = PayableParty.objects.get(name="Hay Supplier")
        self.assertEqual(party.finance_domain, FinanceDomain.GENERAL)

    def test_create_obligation_post(self):
        party = PayableParty.objects.create(team=self.team, name="Farrier", finance_domain=FinanceDomain.GENERAL)
        response = self.client.post(reverse("finance_payable_obligation_add", args=[party.pk]), {
            "expense_category": self.category.pk,
            "description": "September trims",
            "amount": "240.00",
            "obligation_date": "2026-09-19",
            "due_date": "2026-09-30",
            "season": "",
            "reference": "INV-100",
            "notes": "",
        })
        self.assertEqual(response.status_code, 302)
        obligation = PayableObligation.objects.get(party=party)
        self.assertEqual(obligation.amount, Decimal("240.00"))

    def test_record_payment_post_creates_expense_transaction(self):
        party = PayableParty.objects.create(team=self.team, name="Feed Store", finance_domain=FinanceDomain.GENERAL)
        obligation = PayableObligation.objects.create(
            party=party, expense_category=self.category, description="Feed",
            amount=Decimal("300.00"), obligation_date=date(2026, 9, 19),
        )
        response = self.client.post(reverse("finance_payable_payment_add", args=[obligation.pk]), {
            "amount": "125.00",
            "paid_date": "2026-09-19",
            "payment_account": self.bank.pk,
            "method": "ACH",
            "reference": "ACH-1",
            "notes": "",
        })
        self.assertEqual(response.status_code, 302)
        payment = PayablePayment.objects.get(obligation=obligation)
        self.assertEqual(payment.amount, Decimal("125.00"))
        self.assertEqual(payment.financial_transaction.kind, FinancialTransaction.Kind.EXPENSE)
        self.assertEqual(obligation.balance, Decimal("175.00"))

    def test_void_payment_post_restores_balance_and_voids_ledger(self):
        party = PayableParty.objects.create(team=self.team, name="Vet", finance_domain=FinanceDomain.GENERAL)
        obligation = PayableObligation.objects.create(
            party=party, expense_category=self.category, description="Farm call",
            amount=Decimal("200.00"), obligation_date=date(2026, 9, 19),
        )
        self.client.post(reverse("finance_payable_payment_add", args=[obligation.pk]), {
            "amount": "200.00", "paid_date": "2026-09-19", "payment_account": self.bank.pk,
            "method": "Check", "reference": "1001", "notes": "",
        })
        payment = PayablePayment.objects.get(obligation=obligation)
        response = self.client.post(reverse("finance_payable_payment_void", args=[obligation.pk, payment.pk]), {
            "reason": "Check was cancelled",
        })
        self.assertEqual(response.status_code, 302)
        payment.refresh_from_db()
        payment.financial_transaction.refresh_from_db()
        self.assertEqual(payment.status, PayablePayment.Status.VOID)
        self.assertEqual(payment.financial_transaction.status, FinancialTransaction.Status.VOID)
        self.assertEqual(obligation.balance, Decimal("200.00"))

    def test_payment_detail_renders(self):
        party = PayableParty.objects.create(team=self.team, name="Supplier", finance_domain=FinanceDomain.GENERAL)
        obligation = PayableObligation.objects.create(
            party=party, expense_category=self.category, description="Supplies",
            amount=Decimal("50.00"), obligation_date=date(2026, 9, 19),
        )
        response = self.client.get(reverse("finance_payable_obligation_detail", args=[obligation.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Record payment")
