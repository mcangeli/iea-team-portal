from datetime import date, datetime, time
from decimal import Decimal
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from portal.model_modules.finance import FinanceDomain, ReceivableAccount, ReceivableAccountPerson, ReceivableBillingRule, ReceivableCharge
from portal.model_modules.lessons import LessonAttendanceRecord, LessonOccurrence, LessonProgram, LessonSeries
from portal.model_modules.people import Person
from portal.models import Team
from portal.services.lesson_billing import bill_lesson_occurrence

class LessonReceivablesBillingTests(TestCase):
    def setUp(self):
        self.team=Team.objects.create(name="Lesson Billing Barn")
        self.rider=Person.objects.create(team=self.team,first_name="Riley",last_name="Student")
        self.program=LessonProgram.objects.create(team=self.team,name="Barn Lessons")
        self.series=LessonSeries.objects.create(program=self.program,name="Private Lessons")
        self.occurrence=LessonOccurrence.objects.create(series=self.series,title="Private lesson",starts_at=timezone.make_aware(datetime(2026,9,19,16,0)),status=LessonOccurrence.Status.COMPLETED)
        self.attendance=LessonAttendanceRecord.objects.create(occurrence=self.occurrence,person=self.rider,status=LessonAttendanceRecord.Status.PRESENT)
        self.account=ReceivableAccount.objects.create(team=self.team,name="Riley Account",finance_domain=FinanceDomain.GENERAL,primary_person=self.rider)
        self.rule=ReceivableBillingRule.objects.create(account=self.account,description="Private lesson",amount=Decimal("65.00"),cadence=ReceivableBillingRule.Cadence.SERVICE,charge_type="lesson",due_days=7)

    def test_completed_present_lesson_generates_receivable(self):
        result=bill_lesson_occurrence(occurrence=self.occurrence,rule=self.rule,person_accounts={self.rider.pk:self.account})
        self.assertEqual(len(result.generated),1);charge=result.generated[0]
        self.assertEqual(charge.account,self.account);self.assertEqual(charge.amount,Decimal("65.00"));self.assertEqual(charge.due_date,date(2026,9,26))

    def test_lesson_billing_retry_is_idempotent(self):
        first=bill_lesson_occurrence(occurrence=self.occurrence,rule=self.rule,person_accounts={self.rider.pk:self.account})
        second=bill_lesson_occurrence(occurrence=self.occurrence,rule=self.rule,person_accounts={self.rider.pk:self.account})
        self.assertEqual(len(first.generated),1);self.assertEqual(len(second.existing),1);self.assertEqual(ReceivableCharge.objects.count(),1)

    def test_absent_attendance_is_not_billed(self):
        self.attendance.status=LessonAttendanceRecord.Status.ABSENT;self.attendance.save()
        result=bill_lesson_occurrence(occurrence=self.occurrence,rule=self.rule,person_accounts={self.rider.pk:self.account})
        self.assertEqual(len(result.generated),0);self.assertEqual(len(result.skipped),1)

    def test_scheduled_occurrence_cannot_be_billed(self):
        self.occurrence.status=LessonOccurrence.Status.SCHEDULED;self.occurrence.save()
        with self.assertRaises(ValidationError):bill_lesson_occurrence(occurrence=self.occurrence,rule=self.rule,person_accounts={self.rider.pk:self.account})

    def test_missing_account_is_skipped_not_guessed(self):
        result=bill_lesson_occurrence(occurrence=self.occurrence,rule=self.rule,person_accounts={})
        self.assertEqual(len(result.generated),0);self.assertEqual(len(result.skipped),1)

    def test_participant_link_resolves_account_automatically(self):
        ReceivableAccountPerson.objects.create(account=self.account,person=self.rider,role=ReceivableAccountPerson.Role.PARTICIPANT)
        result=bill_lesson_occurrence(occurrence=self.occurrence,rule=self.rule)
        self.assertEqual(len(result.generated),1);self.assertEqual(result.generated[0].account,self.account)

    def test_no_participant_link_is_skipped(self):
        result=bill_lesson_occurrence(occurrence=self.occurrence,rule=self.rule)
        self.assertEqual(len(result.generated),0);self.assertEqual(len(result.skipped),1)

    def test_inactive_participant_link_is_skipped(self):
        ReceivableAccountPerson.objects.create(account=self.account,person=self.rider,role=ReceivableAccountPerson.Role.PARTICIPANT,active=False)
        result=bill_lesson_occurrence(occurrence=self.occurrence,rule=self.rule)
        self.assertEqual(len(result.generated),0);self.assertEqual(len(result.skipped),1)

    def test_ambiguous_participant_accounts_are_rejected(self):
        ReceivableAccountPerson.objects.create(account=self.account,person=self.rider,role=ReceivableAccountPerson.Role.PARTICIPANT)
        other=ReceivableAccount.objects.create(team=self.team,name="Second Riley Account",finance_domain=FinanceDomain.GENERAL)
        ReceivableAccountPerson.objects.create(account=other,person=self.rider,role=ReceivableAccountPerson.Role.PARTICIPANT)
        with self.assertRaises(ValidationError):bill_lesson_occurrence(occurrence=self.occurrence,rule=self.rule)

    def test_iea_participant_link_does_not_resolve_for_general_rule(self):
        iea=ReceivableAccount.objects.create(team=self.team,name="IEA Riley",finance_domain=FinanceDomain.IEA)
        ReceivableAccountPerson.objects.create(account=iea,person=self.rider,role=ReceivableAccountPerson.Role.PARTICIPANT)
        result=bill_lesson_occurrence(occurrence=self.occurrence,rule=self.rule)
        self.assertEqual(len(result.generated),0);self.assertEqual(len(result.skipped),1)

class LessonBillingUITests(TestCase):
    def setUp(self):
        self.team=Team.objects.create(name="Lesson Billing UI Barn")
        self.admin=User.objects.create_user(username="billing-admin",password="test-pass")
        self.admin.profile.team=self.team;self.admin.profile.role="admin";self.admin.profile.save()
        self.client.login(username="billing-admin",password="test-pass")
        self.rider=Person.objects.create(team=self.team,first_name="Alex",last_name="Rider")
        self.program=LessonProgram.objects.create(team=self.team,name="Academy")
        self.series=LessonSeries.objects.create(program=self.program,name="Private")
        self.occurrence=LessonOccurrence.objects.create(series=self.series,title="Friday lesson",starts_at=timezone.make_aware(datetime(2026,9,18,16,0)),status=LessonOccurrence.Status.COMPLETED)
        LessonAttendanceRecord.objects.create(occurrence=self.occurrence,person=self.rider,status=LessonAttendanceRecord.Status.PRESENT)
        self.account=ReceivableAccount.objects.create(team=self.team,name="Alex Account",finance_domain=FinanceDomain.GENERAL,primary_person=self.rider)
        ReceivableAccountPerson.objects.create(account=self.account,person=self.rider,role=ReceivableAccountPerson.Role.PARTICIPANT)
        self.rule=ReceivableBillingRule.objects.create(account=self.account,description="Private lesson",amount=Decimal("70.00"),cadence=ReceivableBillingRule.Cadence.SERVICE,charge_type="lesson")

    def test_completed_occurrence_offers_billing_rule(self):
        response=self.client.get(reverse("lesson_occurrence_detail",args=[self.occurrence.pk]))
        self.assertEqual(response.status_code,200);self.assertContains(response,"Lesson billing");self.assertContains(response,"Private lesson")

    def test_billing_preview_shows_ready_participant(self):
        response=self.client.get(reverse("lesson_occurrence_detail",args=[self.occurrence.pk]),{"billing_rule":self.rule.pk})
        self.assertEqual(response.status_code,200);self.assertContains(response,"Ready to bill");self.assertContains(response,"Alex Rider")

    def test_post_lesson_billing_creates_charge(self):
        response=self.client.post(reverse("lesson_occurrence_bill",args=[self.occurrence.pk]),{"billing_rule":self.rule.pk})
        self.assertEqual(response.status_code,302);self.assertEqual(ReceivableCharge.objects.filter(account=self.account,billing_rule=self.rule).count(),1)

    def test_post_lesson_billing_is_safe_to_retry(self):
        url=reverse("lesson_occurrence_bill",args=[self.occurrence.pk])
        self.client.post(url,{"billing_rule":self.rule.pk});self.client.post(url,{"billing_rule":self.rule.pk})
        self.assertEqual(ReceivableCharge.objects.filter(account=self.account,billing_rule=self.rule).count(),1)

    def test_occurrence_hides_service_rules_for_unrelated_accounts(self):
        other_person=Person.objects.create(team=self.team,first_name="Other",last_name="Rider")
        other_account=ReceivableAccount.objects.create(team=self.team,name="Other Account",finance_domain=FinanceDomain.GENERAL,primary_person=other_person)
        other_rule=ReceivableBillingRule.objects.create(account=other_account,description="Unrelated service",amount=Decimal("90.00"),cadence=ReceivableBillingRule.Cadence.SERVICE)
        response=self.client.get(reverse("lesson_occurrence_detail",args=[self.occurrence.pk]))
        self.assertContains(response,"Private lesson");self.assertNotContains(response,"Unrelated service")
