from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from portal.model_modules.finance import FinanceDomain, ReceivableAccount, ReceivableCredit, ReceivableCreditRule
from portal.models import Season, Team
from portal.services.finance_earned_credits import calculate_earned_credit, earned_credit_key, generate_earned_credit, generate_rule_credit


class EarnedReceivableCreditTests(TestCase):
    def setUp(self):
        self.team=Team.objects.create(name="Credit Barn")
        self.account=ReceivableAccount.objects.create(team=self.team,name="Family Board",finance_domain=FinanceDomain.GENERAL)

    def test_work_credit_posts_without_changing_charge(self):
        credit,created=generate_earned_credit(account=self.account,source_type="barn_work",source_id="shift-91",credit_date=date(2026,9,19),description="Barn work credit",amount=Decimal("150.00"),credit_type="work")
        self.assertTrue(created);self.assertEqual(credit.amount,Decimal("150.00"));self.assertEqual(credit.generation_key,"earned:barn_work:shift-91")

    def test_horse_use_credit_is_retry_safe(self):
        kwargs=dict(account=self.account,source_type="lesson_horse_use",source_id="lesson-42:horse-7",credit_date=date(2026,9,19),description="Horse use credit",amount=Decimal("75.00"),credit_type="horse_use")
        first,created=generate_earned_credit(**kwargs);second,created_again=generate_earned_credit(**kwargs)
        self.assertTrue(created);self.assertFalse(created_again);self.assertEqual(first.pk,second.pk);self.assertEqual(ReceivableCredit.objects.count(),1)

    def test_same_source_can_credit_different_accounts(self):
        other=ReceivableAccount.objects.create(team=self.team,name="Other Family",finance_domain=FinanceDomain.GENERAL)
        one,_=generate_earned_credit(account=self.account,source_type="barn_work",source_id=1,credit_date=date(2026,9,19),description="Work",amount=10)
        two,_=generate_earned_credit(account=other,source_type="barn_work",source_id=1,credit_date=date(2026,9,19),description="Work",amount=10)
        self.assertNotEqual(one.pk,two.pk)

    def test_credit_rejects_nonpositive_amount(self):
        with self.assertRaises(ValidationError):generate_earned_credit(account=self.account,source_type="barn_work",source_id=1,credit_date=date(2026,9,19),description="Work",amount=0)

    def test_credit_rejects_foreign_season(self):
        other=Team.objects.create(name="Other Barn");season=Season.objects.create(team=other,name="2026",start_date=date(2026,1,1),end_date=date(2026,12,31))
        with self.assertRaises(ValidationError):generate_earned_credit(account=self.account,source_type="barn_work",source_id=1,credit_date=date(2026,9,19),description="Work",amount=10,season=season)

    def test_source_identity_is_required(self):
        with self.assertRaises(ValidationError):earned_credit_key("",1)

class ReceivableCreditRuleTests(TestCase):
    def setUp(self):
        self.team=Team.objects.create(name="Rule Barn")
        self.account=ReceivableAccount.objects.create(team=self.team,name="Family Board",finance_domain=FinanceDomain.GENERAL)

    def test_fixed_horse_use_credit(self):
        rule=ReceivableCreditRule.objects.create(team=self.team,name="Lesson horse use",source_type="lesson_horse_use",calculation=ReceivableCreditRule.Calculation.FIXED,rate=Decimal("25.00"),credit_type="horse_use")
        credit,created=generate_rule_credit(rule=rule,account=self.account,source_id="lesson-42:horse-7",credit_date=date(2026,9,19))
        self.assertTrue(created);self.assertEqual(credit.amount,Decimal("25.00"));self.assertEqual(credit.credit_type,"horse_use")

    def test_hourly_work_credit_uses_quantity(self):
        rule=ReceivableCreditRule.objects.create(team=self.team,name="Barn work",source_type="barn_work",calculation=ReceivableCreditRule.Calculation.QUANTITY,rate=Decimal("15.00"),credit_type="work")
        credit,_=generate_rule_credit(rule=rule,account=self.account,source_id="shift-12",credit_date=date(2026,9,19),quantity=Decimal("3.5"))
        self.assertEqual(credit.amount,Decimal("52.50"))

    def test_quantity_rule_requires_positive_quantity(self):
        rule=ReceivableCreditRule.objects.create(team=self.team,name="Barn work",source_type="barn_work",calculation=ReceivableCreditRule.Calculation.QUANTITY,rate=Decimal("15.00"))
        with self.assertRaises(ValidationError):calculate_earned_credit(rule)
        with self.assertRaises(ValidationError):calculate_earned_credit(rule,quantity=0)

    def test_inactive_credit_rule_cannot_generate(self):
        rule=ReceivableCreditRule.objects.create(team=self.team,name="Old credit",source_type="work",rate=Decimal("10.00"),active=False)
        with self.assertRaises(ValidationError):generate_rule_credit(rule=rule,account=self.account,source_id=1,credit_date=date(2026,9,19))

    def test_credit_rule_enforces_finance_domain(self):
        rule=ReceivableCreditRule.objects.create(team=self.team,name="IEA work",source_type="iea_work",finance_domain=FinanceDomain.IEA,rate=Decimal("10.00"))
        with self.assertRaises(ValidationError):generate_rule_credit(rule=rule,account=self.account,source_id=1,credit_date=date(2026,9,19))
