"""Operational adapters that translate ArenaLine activity into earned credits."""
from decimal import Decimal

from django.core.exceptions import ValidationError

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


def credit_lesson_horse_use(*,assignment,owner,rule,description=None,season=None,notes=""):
    """Credit a horse owner when their horse is used by someone else in a completed lesson."""
    occurrence=assignment.occurrence
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
