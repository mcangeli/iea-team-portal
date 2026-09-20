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
