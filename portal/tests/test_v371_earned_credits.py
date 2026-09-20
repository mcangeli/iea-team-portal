from datetime import date, datetime, timedelta
from django.utils import timezone
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from portal.model_modules.station import WorkShiftEntry
from portal.model_modules.finance import FinanceDomain, ReceivableAccount, ReceivableAccountPerson, ReceivableCredit, ReceivableCreditRule
from portal.model_modules.people import Person
from portal.model_modules.horses import Horse
from portal.model_modules.barn_participation import HorsePersonRelationship
from portal.model_modules.lessons import LessonAssignment, LessonOccurrence, LessonProgram, LessonSeries
from portal.models import Season, Team, UserProfile
from portal.services.finance_earned_credits import calculate_earned_credit, earned_credit_key, generate_earned_credit, generate_rule_credit
from portal.services.finance_operational_credits import credit_lesson_horse_use, credit_work_hours, credit_approved_work_shift


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

    def test_direct_credit_rejects_foreign_credit_rule(self):
        other=Team.objects.create(name="Other Rule Barn")
        rule=ReceivableCreditRule.objects.create(team=other,name="Foreign work",source_type="barn_work",rate=Decimal("10.00"))
        with self.assertRaises(ValidationError):
            generate_earned_credit(account=self.account,source_type="barn_work",source_id=1,credit_date=date(2026,9,19),description="Work",amount=10,credit_rule=rule)

    def test_direct_credit_rule_requires_matching_source_type(self):
        rule=ReceivableCreditRule.objects.create(team=self.team,name="Horse use",source_type="lesson_horse_use",rate=Decimal("25.00"))
        with self.assertRaises(ValidationError):
            generate_earned_credit(account=self.account,source_type="barn_work",source_id=1,credit_date=date(2026,9,19),description="Work",amount=10,credit_rule=rule)

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

    def test_rule_generated_credit_retains_rule(self):
        rule=ReceivableCreditRule.objects.create(team=self.team,name="Horse use trace",source_type="lesson_horse_use",rate=Decimal("25.00"))
        credit,_=generate_rule_credit(rule=rule,account=self.account,source_id="lesson-99",credit_date=date(2026,9,19))
        self.assertEqual(credit.credit_rule,rule)
        self.assertTrue(credit.generation_key.startswith(f"credit-rule:{rule.pk}:"))

    def test_two_rules_can_credit_same_source_on_same_account(self):
        first_rule=ReceivableCreditRule.objects.create(team=self.team,name="Owner use credit",source_type="lesson_horse_use",rate=Decimal("25.00"))
        second_rule=ReceivableCreditRule.objects.create(team=self.team,name="Bonus use credit",source_type="lesson_horse_use",rate=Decimal("10.00"))
        first,first_created=generate_rule_credit(rule=first_rule,account=self.account,source_id="lesson-100",credit_date=date(2026,9,19))
        second,second_created=generate_rule_credit(rule=second_rule,account=self.account,source_id="lesson-100",credit_date=date(2026,9,19))
        self.assertTrue(first_created);self.assertTrue(second_created);self.assertNotEqual(first.pk,second.pk)
        self.assertEqual(ReceivableCredit.objects.filter(account=self.account,source_id="lesson-100").count(),2)

    def test_same_rule_same_source_remains_idempotent(self):
        rule=ReceivableCreditRule.objects.create(team=self.team,name="Retry trace",source_type="lesson_horse_use",rate=Decimal("25.00"))
        first,_=generate_rule_credit(rule=rule,account=self.account,source_id="lesson-101",credit_date=date(2026,9,19))
        second,created=generate_rule_credit(rule=rule,account=self.account,source_id="lesson-101",credit_date=date(2026,9,19))
        self.assertFalse(created);self.assertEqual(first.pk,second.pk);self.assertEqual(second.credit_rule,rule)

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

class BarnWorkCreditAdapterTests(TestCase):
    def setUp(self):
        self.team=Team.objects.create(name="Working Barn")
        self.person=Person.objects.create(team=self.team,first_name="Alex",last_name="Worker")
        self.account=ReceivableAccount.objects.create(team=self.team,name="Worker Family",finance_domain=FinanceDomain.GENERAL)
        ReceivableAccountPerson.objects.create(account=self.account,person=self.person,role=ReceivableAccountPerson.Role.PARTICIPANT)
        self.rule=ReceivableCreditRule.objects.create(team=self.team,name="Barn work",source_type="barn_work",calculation=ReceivableCreditRule.Calculation.QUANTITY,rate=Decimal("15.00"),credit_type="work")

    def test_work_hours_resolve_family_account_and_credit_it(self):
        credit,created,status=credit_work_hours(person=self.person,rule=self.rule,work_record_id=44,work_date=date(2026,9,19),hours=Decimal("4.25"))
        self.assertTrue(created);self.assertEqual(status,"generated");self.assertEqual(credit.account,self.account);self.assertEqual(credit.amount,Decimal("63.75"))

    def test_work_record_retry_is_idempotent(self):
        kwargs=dict(person=self.person,rule=self.rule,work_record_id=44,work_date=date(2026,9,19),hours=2)
        first,_,_=credit_work_hours(**kwargs);second,created,status=credit_work_hours(**kwargs)
        self.assertFalse(created);self.assertEqual(status,"existing");self.assertEqual(first.pk,second.pk)

    def test_worker_without_receivable_account_is_not_guessed(self):
        other=Person.objects.create(team=self.team,first_name="No",last_name="Account")
        credit,created,status=credit_work_hours(person=other,rule=self.rule,work_record_id=45,work_date=date(2026,9,19),hours=2)
        self.assertIsNone(credit);self.assertFalse(created);self.assertEqual(status,"no_account")

    def test_work_adapter_rejects_wrong_rule_source(self):
        rule=ReceivableCreditRule.objects.create(team=self.team,name="Horse use",source_type="lesson_horse_use",rate=25)
        with self.assertRaises(ValidationError):credit_work_hours(person=self.person,rule=rule,work_record_id=46,work_date=date(2026,9,19),hours=1)

class LessonHorseUseCreditAdapterTests(TestCase):
    def setUp(self):
        self.team=Team.objects.create(name="Horse Credit Barn")
        self.owner=Person.objects.create(team=self.team,first_name="Horse",last_name="Owner")
        self.rider=Person.objects.create(team=self.team,first_name="Lesson",last_name="Rider")
        self.account=ReceivableAccount.objects.create(team=self.team,name="Owner Family",finance_domain=FinanceDomain.GENERAL)
        ReceivableAccountPerson.objects.create(account=self.account,person=self.owner,role=ReceivableAccountPerson.Role.PARTICIPANT)
        self.horse=Horse.objects.create(team=self.team,name="Comet")
        program=LessonProgram.objects.create(team=self.team,name="Barn Lessons")
        series=LessonSeries.objects.create(program=program,name="Tuesday")
        self.occurrence=LessonOccurrence.objects.create(series=series,title="Tuesday Lesson",starts_at=timezone.make_aware(datetime(2026,9,19,15,0)),status=LessonOccurrence.Status.COMPLETED)
        self.assignment=LessonAssignment.objects.create(occurrence=self.occurrence,person=self.rider,horse=self.horse,role=LessonAssignment.Role.PARTICIPANT)
        self.rule=ReceivableCreditRule.objects.create(team=self.team,name="Lesson horse use",source_type="lesson_horse_use",calculation=ReceivableCreditRule.Calculation.FIXED,rate=Decimal("25.00"),credit_type="horse_use")

    def test_completed_lesson_horse_use_credits_owner_account(self):
        credit,created,status=credit_lesson_horse_use(assignment=self.assignment,owner=self.owner,rule=self.rule)
        self.assertTrue(created);self.assertEqual(status,"generated");self.assertEqual(credit.account,self.account);self.assertEqual(credit.amount,Decimal("25.00"));self.assertIn("Comet",credit.description)

    def test_lesson_horse_use_retry_is_idempotent(self):
        first,_,_=credit_lesson_horse_use(assignment=self.assignment,owner=self.owner,rule=self.rule)
        second,created,status=credit_lesson_horse_use(assignment=self.assignment,owner=self.owner,rule=self.rule)
        self.assertFalse(created);self.assertEqual(status,"existing");self.assertEqual(first.pk,second.pk)

    def test_owner_riding_own_horse_does_not_earn_credit(self):
        self.assignment.person=self.owner;self.assignment.save()
        credit,created,status=credit_lesson_horse_use(assignment=self.assignment,owner=self.owner,rule=self.rule)
        self.assertIsNone(credit);self.assertFalse(created);self.assertEqual(status,"owner_use")

    def test_horse_relationship_automatically_resolves_credit_recipient(self):
        HorsePersonRelationship.objects.create(team=self.team,horse=self.horse,person=self.owner,relationship_type=HorsePersonRelationship.RelationshipType.OWNER,credit_recipient=True)
        credit,created,status=credit_lesson_horse_use(assignment=self.assignment,rule=self.rule)
        self.assertTrue(created);self.assertEqual(status,"generated");self.assertEqual(credit.account,self.account)

    def test_horse_without_credit_recipient_is_not_guessed(self):
        credit,created,status=credit_lesson_horse_use(assignment=self.assignment,rule=self.rule)
        self.assertIsNone(credit);self.assertFalse(created);self.assertEqual(status,"no_credit_recipient")

    def test_horse_relationship_rejects_cross_organization_person(self):
        other_team=Team.objects.create(name="Other Barn")
        other=Person.objects.create(team=other_team,first_name="Other",last_name="Owner")
        relationship=HorsePersonRelationship(team=self.team,horse=self.horse,person=other,relationship_type=HorsePersonRelationship.RelationshipType.OWNER)
        with self.assertRaises(ValidationError):relationship.full_clean()

    def test_only_one_active_credit_recipient_per_horse(self):
        HorsePersonRelationship.objects.create(team=self.team,horse=self.horse,person=self.owner,relationship_type=HorsePersonRelationship.RelationshipType.OWNER,credit_recipient=True)
        other=Person.objects.create(team=self.team,first_name="Second",last_name="Owner")
        relationship=HorsePersonRelationship(team=self.team,horse=self.horse,person=other,relationship_type=HorsePersonRelationship.RelationshipType.CO_OWNER if hasattr(HorsePersonRelationship.RelationshipType,"CO_OWNER") else HorsePersonRelationship.RelationshipType.BOARDER,credit_recipient=True)
        with self.assertRaises(ValidationError):relationship.validate_constraints()

    def test_inactive_relationship_cannot_be_credit_recipient(self):
        relationship=HorsePersonRelationship(team=self.team,horse=self.horse,person=self.owner,relationship_type=HorsePersonRelationship.RelationshipType.OWNER,active=False,credit_recipient=True)
        with self.assertRaises(ValidationError):relationship.full_clean()

    def test_scheduled_lesson_cannot_generate_horse_use_credit(self):
        self.occurrence.status=LessonOccurrence.Status.SCHEDULED;self.occurrence.save()
        with self.assertRaises(ValidationError):credit_lesson_horse_use(assignment=self.assignment,owner=self.owner,rule=self.rule)


class ApprovedWorkShiftCreditTests(TestCase):
    def setUp(self):
        self.team=Team.objects.create(name="Shift Credit Barn")
        self.user=User.objects.create_user(username="shift-credit-admin",password="pass12345")
        p=self.user.profile;p.team=self.team;p.role=UserProfile.Role.ADMIN;p.save(update_fields=["team","role"])
        self.person=Person.objects.create(team=self.team,first_name="Jamie",last_name="Worker")
        self.account=ReceivableAccount.objects.create(team=self.team,name="Jamie Account",finance_domain=FinanceDomain.GENERAL)
        ReceivableAccountPerson.objects.create(account=self.account,person=self.person,role=ReceivableAccountPerson.Role.PARTICIPANT)
        self.rule=ReceivableCreditRule.objects.create(team=self.team,finance_domain=FinanceDomain.GENERAL,name="Barn Work Credit",source_type="barn_work",calculation=ReceivableCreditRule.Calculation.QUANTITY,rate=Decimal("15.00"),credit_type="work")

    def _shift(self,approved=True,closed=True):
        start=timezone.now()-timedelta(hours=2)
        return WorkShiftEntry.objects.create(team=self.team,person=self.person,role=WorkShiftEntry.Role.WORKING_STUDENT,clock_in=start,clock_out=start+timedelta(minutes=90) if closed else None,approved_by=self.user if approved else None,approved_at=timezone.now() if approved else None)

    def test_approved_shift_generates_credit_from_exact_duration(self):
        shift=self._shift()
        credit,created,status=credit_approved_work_shift(shift=shift,rule=self.rule)
        self.assertTrue(created);self.assertEqual(status,"generated");self.assertEqual(credit.amount,Decimal("22.50"))
        self.assertEqual(credit.source_id,f"work:{shift.pk}");self.assertEqual(credit.credit_rule,self.rule)

    def test_approved_shift_credit_retry_is_idempotent(self):
        shift=self._shift()
        first,_,_=credit_approved_work_shift(shift=shift,rule=self.rule)
        second,created,status=credit_approved_work_shift(shift=shift,rule=self.rule)
        self.assertFalse(created);self.assertEqual(status,"existing");self.assertEqual(first.pk,second.pk)

    def test_unapproved_shift_cannot_generate_credit(self):
        shift=self._shift(approved=False)
        with self.assertRaises(ValidationError):credit_approved_work_shift(shift=shift,rule=self.rule)

    def test_open_shift_cannot_generate_credit(self):
        shift=self._shift(approved=False,closed=False)
        with self.assertRaises(ValidationError):credit_approved_work_shift(shift=shift,rule=self.rule)
