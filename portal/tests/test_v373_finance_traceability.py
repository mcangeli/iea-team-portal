from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.capabilities import OrganizationCapabilityAssignment
from portal.model_modules.finance import FinanceDomain, PayableObligation, PayableParty, PayablePayment, ReceivableAccount, ReceivablePayment
from portal.model_modules.people import Person
from portal.models import FinancialAccount, FinancialCategory, FinancialTransaction, Team, UserProfile
from portal.services.finance_traceability import transaction_trace


class V373FinanceTraceabilityTests(TestCase):
    def setUp(self):
        self.team=Team.objects.create(name="Trace Barn")
        self.user=User.objects.create_user(username="trace-admin",password="pass12345")
        self.user.profile.team=self.team;self.user.profile.role=UserProfile.Role.ADMIN;self.user.profile.save(update_fields=["team","role"])
        self.account=FinancialAccount.objects.create(team=self.team,name="Checking",finance_domain=FinanceDomain.GENERAL)
        self.income=FinancialCategory.objects.create(team=self.team,name="Board",kind=FinancialCategory.Kind.INCOME)
        self.expense=FinancialCategory.objects.create(team=self.team,name="Hay",kind=FinancialCategory.Kind.EXPENSE)

    def _tx(self,kind,category,description):
        return FinancialTransaction.objects.create(team=self.team,transaction_date=date(2026,9,20),kind=kind,account=self.account,category=category,amount=Decimal("100.00"),description=description)

    def test_trace_identifies_receivable_payment(self):
        tx=self._tx(FinancialTransaction.Kind.INCOME,self.income,"Board payment")
        account=ReceivableAccount.objects.create(team=self.team,name="Boarder",finance_domain=FinanceDomain.GENERAL)
        payment=ReceivablePayment.objects.create(account=account,amount=Decimal("100.00"),received_date=date(2026,9,20),deposit_account=self.account,income_category=self.income,financial_transaction=tx)
        trace=transaction_trace(tx)
        self.assertEqual(trace.source_kind,"receivable_payment")
        self.assertEqual(trace.source_object.pk,payment.pk)

    def test_trace_identifies_payable_payment(self):
        tx=self._tx(FinancialTransaction.Kind.EXPENSE,self.expense,"Hay payment")
        party=PayableParty.objects.create(team=self.team,name="Hay Co",finance_domain=FinanceDomain.GENERAL)
        obligation=PayableObligation.objects.create(party=party,expense_category=self.expense,description="Hay",amount=Decimal("100.00"),obligation_date=date(2026,9,1))
        payment=PayablePayment.objects.create(obligation=obligation,amount=Decimal("100.00"),paid_date=date(2026,9,20),payment_account=self.account,financial_transaction=tx)
        trace=transaction_trace(tx)
        self.assertEqual(trace.source_kind,"payable_payment")
        self.assertEqual(trace.source_object.pk,payment.pk)

    def test_direct_ledger_transaction_has_direct_origin(self):
        tx=self._tx(FinancialTransaction.Kind.EXPENSE,self.expense,"Direct expense")
        self.assertEqual(transaction_trace(tx).source_kind,"ledger")

    def test_transaction_detail_renders_trace(self):
        tx=self._tx(FinancialTransaction.Kind.INCOME,self.income,"Board payment")
        account=ReceivableAccount.objects.create(team=self.team,name="Boarder",finance_domain=FinanceDomain.GENERAL)
        ReceivablePayment.objects.create(account=account,amount=Decimal("100.00"),received_date=date(2026,9,20),deposit_account=self.account,income_category=self.income,financial_transaction=tx)
        self.client.force_login(self.user)
        response=self.client.get(reverse("finance_transaction_detail",args=[tx.pk]))
        self.assertEqual(response.status_code,200)
        self.assertContains(response,"Receivable payment")
        self.assertContains(response,"Boarder")

    def test_iea_only_user_cannot_open_general_transaction(self):
        user=User.objects.create_user(username="trace-iea",password="pass12345")
        user.profile.team=self.team;user.profile.save(update_fields=["team"])
        person=Person.objects.create(team=self.team,user=user,first_name="Trace",last_name="IEA")
        OrganizationCapabilityAssignment.objects.create(team=self.team,person=person,capability=OrganizationCapabilityAssignment.Capability.MANAGE_IEA_FINANCE)
        tx=self._tx(FinancialTransaction.Kind.EXPENSE,self.expense,"General expense")
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("finance_transaction_detail",args=[tx.pk])).status_code,403)
