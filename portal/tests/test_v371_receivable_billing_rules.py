from datetime import date
from decimal import Decimal
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from portal.model_modules.finance import FinanceDomain, ReceivableAccount, ReceivableAccountPerson, ReceivableBillingRule, ReceivableCharge
from portal.model_modules.people import Person
from portal.models import Season, Team
from portal.services.finance_billing import generate_charge, generate_monthly_charge, generate_monthly_charges, generate_service_charge
from portal.services.finance_service_billing import bill_person_service

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

    def test_monthly_generation_uses_first_day_and_is_idempotent(self):
        charge,created=generate_monthly_charge(rule=self.rule,billing_month=date(2026,9,19))
        again,created_again=generate_monthly_charge(rule=self.rule,billing_month=date(2026,9,30))
        self.assertTrue(created);self.assertFalse(created_again);self.assertEqual(charge.pk,again.pk)
        self.assertEqual(charge.charge_date,date(2026,9,1));self.assertEqual(charge.due_date,date(2026,9,11))

    def test_monthly_batch_skips_nonmonthly_and_inactive_rules(self):
        inactive=ReceivableBillingRule.objects.create(account=self.account,description="Inactive",amount=Decimal("10.00"),cadence=ReceivableBillingRule.Cadence.MONTHLY,active=False)
        service=ReceivableBillingRule.objects.create(account=self.account,description="Lesson",amount=Decimal("50.00"),cadence=ReceivableBillingRule.Cadence.SERVICE)
        result=generate_monthly_charges(rules=[self.rule,inactive,service],billing_month=date(2026,9,1))
        self.assertEqual(len(result["generated"]),1);self.assertEqual(ReceivableCharge.objects.count(),1)

    def test_service_generation_is_idempotent_by_source(self):
        rule=ReceivableBillingRule.objects.create(account=self.account,description="Private lesson",amount=Decimal("65.00"),cadence=ReceivableBillingRule.Cadence.SERVICE,charge_type="lesson")
        charge,created=generate_service_charge(rule=rule,source_type="lesson_occurrence",source_id=42,service_date=date(2026,9,19))
        again,created_again=generate_service_charge(rule=rule,source_type="lesson_occurrence",source_id=42,service_date=date(2026,9,19))
        self.assertTrue(created);self.assertFalse(created_again);self.assertEqual(charge.pk,again.pk);self.assertEqual(charge.generation_key,"service:lesson_occurrence:42")

    def test_service_generation_rejects_monthly_rule(self):
        with self.assertRaises(ValidationError):generate_service_charge(rule=self.rule,source_type="lesson",source_id=1,service_date=date(2026,9,19))

class OperationalServiceBillingTests(TestCase):
    def setUp(self):
        self.team=Team.objects.create(name="Service Billing Barn")
        self.person=Person.objects.create(team=self.team,first_name="Casey",last_name="Client")
        self.account=ReceivableAccount.objects.create(team=self.team,name="Casey Account",finance_domain=FinanceDomain.GENERAL)
        self.rule=ReceivableBillingRule.objects.create(account=self.account,description="Training ride",amount=Decimal("45.00"),cadence=ReceivableBillingRule.Cadence.SERVICE,charge_type="training")

    def test_explicit_participant_account_generates_service_charge(self):
        ReceivableAccountPerson.objects.create(account=self.account,person=self.person,role=ReceivableAccountPerson.Role.PARTICIPANT)
        result=bill_person_service(person=self.person,rule=self.rule,source_type="training_ride",source_id=91,service_date=date(2026,9,19))
        self.assertEqual(result.status,"generated");self.assertEqual(result.charge.amount,Decimal("45.00"))

    def test_service_retry_is_idempotent(self):
        ReceivableAccountPerson.objects.create(account=self.account,person=self.person,role=ReceivableAccountPerson.Role.PARTICIPANT)
        first=bill_person_service(person=self.person,rule=self.rule,source_type="training_ride",source_id=91,service_date=date(2026,9,19))
        second=bill_person_service(person=self.person,rule=self.rule,source_type="training_ride",source_id=91,service_date=date(2026,9,19))
        self.assertTrue(first.created);self.assertFalse(second.created);self.assertEqual(second.status,"existing");self.assertEqual(first.charge.pk,second.charge.pk)

    def test_missing_participant_account_skips_without_guessing(self):
        result=bill_person_service(person=self.person,rule=self.rule,source_type="training_ride",source_id=91,service_date=date(2026,9,19))
        self.assertEqual(result.status,"no_account");self.assertIsNone(result.charge)

    def test_different_linked_account_does_not_bill_rule_account(self):
        other=ReceivableAccount.objects.create(team=self.team,name="Other Account",finance_domain=FinanceDomain.GENERAL)
        ReceivableAccountPerson.objects.create(account=other,person=self.person,role=ReceivableAccountPerson.Role.PARTICIPANT)
        result=bill_person_service(person=self.person,rule=self.rule,source_type="training_ride",source_id=91,service_date=date(2026,9,19))
        self.assertEqual(result.status,"different_account");self.assertEqual(ReceivableCharge.objects.count(),0)
