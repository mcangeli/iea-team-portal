from datetime import date, datetime, time
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from portal.model_modules.finance import FinanceDomain, ReceivableAccount, ReceivableBillingRule, ReceivableCharge
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
