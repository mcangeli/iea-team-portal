"""Lesson-to-receivables adapter for ArenaLine v3.7.1."""
from dataclasses import dataclass
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from portal.model_modules.finance import ReceivableBillingRule
from portal.model_modules.lessons import LessonAttendanceRecord, LessonOccurrence
from portal.services.finance_billing import generate_service_charge

BILLABLE_ATTENDANCE={
    LessonAttendanceRecord.Status.PRESENT,
    LessonAttendanceRecord.Status.NO_SHOW,
    LessonAttendanceRecord.Status.MAKEUP,
}

@dataclass(frozen=True)
class LessonBillingResult:
    generated: tuple
    existing: tuple
    skipped: tuple

def _local_date(occurrence):
    return timezone.localtime(occurrence.starts_at).date() if timezone.is_aware(occurrence.starts_at) else occurrence.starts_at.date()

@transaction.atomic
def bill_lesson_occurrence(*,occurrence:LessonOccurrence,rule:ReceivableBillingRule,person_accounts):
    """Bill billable attendance through the generic service-charge boundary.

    person_accounts maps Person IDs to authorized ReceivableAccount objects. The
    adapter deliberately does not guess family/account ownership.
    """
    if not occurrence.pk: raise ValidationError("Lesson occurrence must be saved before billing.")
    if occurrence.status != LessonOccurrence.Status.COMPLETED: raise ValidationError("Only completed lesson occurrences can be billed.")
    if rule.cadence != ReceivableBillingRule.Cadence.SERVICE: raise ValidationError("Lesson billing requires a service billing rule.")
    if rule.account.team_id != occurrence.series.program.team_id: raise ValidationError("Lesson billing rule must belong to the lesson organization.")
    generated=[];existing=[];skipped=[]
    rows=occurrence.attendance_records.select_related("person").order_by("id")
    for attendance in rows:
        if attendance.status not in BILLABLE_ATTENDANCE:
            skipped.append(attendance);continue
        account=person_accounts.get(attendance.person_id)
        if account is None:
            skipped.append(attendance);continue
        if account.team_id != occurrence.series.program.team_id or account.finance_domain != rule.account.finance_domain:
            raise ValidationError("Lesson billing account must belong to the same organization and finance domain.")
        if account.pk != rule.account_id:
            raise ValidationError("Lesson billing rule must target the participant receivable account.")
        charge,created=generate_service_charge(
            rule=rule,
            source_type="lesson_attendance",
            source_id=f"{occurrence.pk}:{attendance.person_id}",
            service_date=_local_date(occurrence),
            description=f"{rule.description} — {occurrence.title}",
        )
        (generated if created else existing).append(charge)
    return LessonBillingResult(tuple(generated),tuple(existing),tuple(skipped))
