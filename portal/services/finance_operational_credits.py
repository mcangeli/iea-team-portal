"""Operational adapters that translate ArenaLine activity into earned credits."""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils import timezone

from portal.services.finance_account_resolution import resolve_participant_account
from portal.services.finance_earned_credits import generate_rule_credit


def credit_person_activity(*,person,rule,source_id,activity_date,quantity=None,
                           description=None,season=None,notes=""):
    """Credit a person's receivable account for verified work/service activity."""
    if person.team_id!=rule.team_id:
        raise ValidationError("Person and credit rule must belong to the same organization.")
    account=resolve_participant_account(person,finance_domain=rule.finance_domain)
    if account is None:
        return None,False,"no_account"
    credit,created=generate_rule_credit(
        rule=rule,account=account,source_id=source_id,credit_date=activity_date,
        quantity=quantity,description=description,season=season,notes=notes,
    )
    return credit,created,("generated" if created else "existing")


def credit_work_hours(*,person,rule,work_record_id,work_date,hours,description=None,
                      season=None,notes=""):
    """Apply a quantity-based earned credit to an approved work record."""
    if rule.source_type!="barn_work":
        raise ValidationError("Barn work credits require a barn_work credit rule.")
    qty=Decimal(hours)
    return credit_person_activity(
        person=person,rule=rule,source_id=f"work:{work_record_id}",
        activity_date=work_date,quantity=qty,description=description,
        season=season,notes=notes,
    )



def credit_approved_work_shift(*,shift,rule,season=None,notes=""):
    """Translate one approved, closed Station shift into an earned barn-work credit."""
    if shift.team_id!=rule.team_id:
        raise ValidationError("Work shift and credit rule must belong to the same organization.")
    if not shift.clock_out:
        raise ValidationError("Open work shifts cannot generate earned credits.")
    if not shift.approved_at:
        raise ValidationError("Work shifts must be approved before they can generate earned credits.")
    seconds=max(0,(shift.clock_out-shift.clock_in).total_seconds())
    hours=(Decimal(str(seconds))/Decimal("3600")).quantize(Decimal("0.0001"))
    if hours<=0:
        raise ValidationError("Work shifts must have a positive duration to generate earned credits.")
    work_date=timezone.localtime(shift.clock_in).date()
    return credit_work_hours(
        person=shift.person,rule=rule,work_record_id=shift.pk,work_date=work_date,
        hours=hours,description=f"{rule.name} — {shift.get_role_display()}",
        season=season,notes=notes or shift.notes,
    )

def credit_lesson_horse_use(*,assignment,rule,owner=None,description=None,season=None,notes=""):
    """Credit a horse owner when their horse is used by someone else in a completed lesson."""
    occurrence=assignment.occurrence
    if owner is None and assignment.horse_id:
        relationship=assignment.horse.person_relationships.filter(active=True,credit_recipient=True).select_related("person").first()
        owner=relationship.person if relationship else None
    if owner is None:
        return None,False,"no_credit_recipient"
    if rule.source_type!="lesson_horse_use":
        raise ValidationError("Lesson horse-use credits require a lesson_horse_use credit rule.")
    if assignment.role!=assignment.Role.PARTICIPANT or not assignment.horse_id:
        raise ValidationError("Lesson horse-use credits require a participant horse assignment.")
    if occurrence.status!=occurrence.Status.COMPLETED:
        raise ValidationError("Horse-use credits may only be posted for completed lessons.")
    if owner.team_id!=occurrence.series.program.team_id:
        raise ValidationError("Horse owner and lesson must belong to the same organization.")
    if assignment.person_id==owner.pk:
        return None,False,"owner_use"
    activity_date=occurrence.starts_at.date()
    return credit_person_activity(
        person=owner,rule=rule,
        source_id=f"lesson:{occurrence.pk}:horse:{assignment.horse_id}:assignment:{assignment.pk}",
        activity_date=activity_date,quantity=1,
        description=description or f"{rule.name} — {assignment.horse.display_name}",
        season=season,notes=notes,
    )
