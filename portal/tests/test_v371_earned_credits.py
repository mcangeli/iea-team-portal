from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from portal.model_modules.finance import FinanceDomain, ReceivableAccount, ReceivableCredit
from portal.models import Season, Team
from portal.services.finance_earned_credits import earned_credit_key, generate_earned_credit


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
