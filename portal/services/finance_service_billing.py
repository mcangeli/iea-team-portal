"""Reusable operational service/usage billing for ArenaLine v3.7.1.

Operational modules should call this boundary rather than constructing
ReceivableCharge rows themselves.
"""
from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction

from portal.model_modules.finance import ReceivableBillingRule
from portal.services.finance_account_resolution import resolve_participant_account
from portal.services.finance_billing import generate_service_charge


@dataclass(frozen=True)
class ServiceBillingResult:
    charge: object | None
    created: bool
    account: object | None
    status: str


@transaction.atomic
def bill_person_service(*, person, rule: ReceivableBillingRule, source_type: str, source_id,
                        service_date, description=None, amount=None, season=None, notes=""):
    """Bill one person for an operational service through an explicit account link.

    The rule remains account-bound in v3.7.1. A participant must resolve to
    exactly that account; ArenaLine never guesses another payer.
    """
    if rule.cadence != ReceivableBillingRule.Cadence.SERVICE:
        raise ValidationError("Only service billing rules can bill operational services.")
    if person.team_id != rule.account.team_id:
        raise ValidationError("Service participant must belong to the billing rule organization.")
    account=resolve_participant_account(person,finance_domain=rule.account.finance_domain)
    if account is None:
        return ServiceBillingResult(None,False,None,"no_account")
    if account.pk != rule.account_id:
        return ServiceBillingResult(None,False,account,"different_account")
    charge,created=generate_service_charge(
        rule=rule,source_type=source_type,source_id=source_id,service_date=service_date,
        description=description,amount=amount,season=season,notes=notes,
    )
    return ServiceBillingResult(charge,created,account,"generated" if created else "existing")
