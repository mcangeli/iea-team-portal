from datetime import date
from decimal import Decimal
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from portal.model_modules.finance import FinanceDomain, ReceivableAccount, ReceivableBillingRule, ReceivableCharge
from portal.models import Season, Team
from portal.services.finance_billing import generate_charge

class ReceivableBillingRuleTests(TestCase):
    def setUp(self):
        self.team=Team.objects.create(name="Billing Barn")
        self.account=ReceivableAccount.objects.create(team=self.team,name="Board Account",finance_domain=FinanceDomain.GENERAL)
        self.rule=ReceivableBillingRule.objects.create(account=self.account,description="Monthly board",amount=Decimal("750.00"),cadence=ReceivableBillingRule.Cadence.MONTHLY,due_days=10,charge_type="board")

    def test_rule_generates_charge_in_existing_ledger(self):
        charge,created=generate_charge(rule=self.rule,generation_key="board:2026-09",charge_date=date(2026,9,1))
        self.assertTrue(created);self.assertEqual(charge.account,self.account);self.assertEqual(charge.amount,Decimal("750.00"));self.assertEqual(charge.due_date,date(2026,9,11));self.assertEqual(charge.charge_type,"board")

    def test_generation_key_makes_retry_idempotent(self):
        first,created=generate_charge(rule=self.rule,generation_key="board:2026-09",charge_date=date(2026,9,1))
        second,created_again=generate_charge(rule=self.rule,generation_key="board:2026-09",charge_date=date(2026,9,1))
        self.assertTrue(created);self.assertFalse(created_again);self.assertEqual(first.pk,second.pk);self.assertEqual(ReceivableCharge.objects.count(),1)

    def test_same_generation_key_is_scoped_to_rule(self):
        other=ReceivableBillingRule.objects.create(account=self.account,description="Training",amount=Decimal("300.00"))
        one,_=generate_charge(rule=self.rule,generation_key="2026-09",charge_date=date(2026,9,1))
        two,_=generate_charge(rule=other,generation_key="2026-09",charge_date=date(2026,9,1))
        self.assertNotEqual(one.pk,two.pk)

    def test_inactive_rule_cannot_generate(self):
        self.rule.active=False;self.rule.save(update_fields=["active"])
        with self.assertRaises(ValidationError):generate_charge(rule=self.rule,generation_key="board:2026-10",charge_date=date(2026,10,1))

    def test_generation_rejects_foreign_season(self):
        other=Team.objects.create(name="Other Barn")
        season=Season.objects.create(team=other,name="2026",start_date=date(2026,1,1),end_date=date(2026,12,31))
        with self.assertRaises(ValidationError):generate_charge(rule=self.rule,generation_key="foreign",charge_date=date(2026,9,1),season=season)

    def test_generated_charge_carries_rule_account_domain(self):
        charge,_=generate_charge(rule=self.rule,generation_key="domain",charge_date=date(2026,9,1))
        self.assertEqual(charge.account.finance_domain,FinanceDomain.GENERAL)
        self.assertEqual(charge.billing_rule,self.rule)
