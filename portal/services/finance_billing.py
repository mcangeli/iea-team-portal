"""v3.7.1 charge generation boundary.

Billing sources generate into the existing ReceivableCharge ledger. generation_key
is caller-owned and makes retries idempotent.
"""
from datetime import timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from portal.model_modules.finance import ReceivableBillingRule, ReceivableCharge

@transaction.atomic
def generate_charge(*,rule:ReceivableBillingRule,generation_key:str,charge_date,description=None,amount=None,season=None,notes=""):
    key=(generation_key or "").strip()
    if not key: raise ValidationError("A generation key is required for generated charges.")
    if not rule.active: raise ValidationError("Inactive billing rules cannot generate charges.")
    if season is not None and season.team_id!=rule.account.team_id: raise ValidationError("Charge season must belong to the account organization.")
    existing=ReceivableCharge.objects.filter(billing_rule=rule,generation_key=key).first()
    if existing:return existing,False
    charge=ReceivableCharge(
        account=rule.account,billing_rule=rule,generation_key=key,season=season,
        description=(description or rule.description).strip(),amount=Decimal(amount) if amount is not None else rule.amount,
        charge_date=charge_date,due_date=charge_date+timedelta(days=rule.due_days),
        charge_type=rule.charge_type,notes=notes.strip(),
    )
    charge.full_clean();charge.save()
    return charge,True


def monthly_generation_key(rule, billing_month):
    """Stable key for one monthly rule/month pair."""
    return f"monthly:{billing_month:%Y-%m}"

@transaction.atomic
def generate_monthly_charge(*, rule:ReceivableBillingRule, billing_month, season=None):
    if rule.cadence != ReceivableBillingRule.Cadence.MONTHLY:
        raise ValidationError("Only monthly billing rules can use monthly generation.")
    charge_date=billing_month.replace(day=1)
    return generate_charge(rule=rule,generation_key=monthly_generation_key(rule,billing_month),charge_date=charge_date,season=season)

@transaction.atomic
def generate_monthly_charges(*, rules, billing_month, season=None):
    """Generate a month's charges for a caller-authorized rule queryset/iterable."""
    generated=[];existing=[]
    for rule in rules:
        if rule.cadence != ReceivableBillingRule.Cadence.MONTHLY or not rule.active:
            continue
        charge,created=generate_monthly_charge(rule=rule,billing_month=billing_month,season=season)
        (generated if created else existing).append(charge)
    return {"generated":tuple(generated),"existing":tuple(existing)}

@transaction.atomic
def generate_service_charge(*, rule:ReceivableBillingRule, source_type:str, source_id, service_date, description=None, amount=None, season=None, notes=""):
    """Stable adapter for operational modules such as lessons, training, leases and care."""
    if rule.cadence != ReceivableBillingRule.Cadence.SERVICE:
        raise ValidationError("Only service billing rules can generate service charges.")
    source=(source_type or "").strip().lower()
    if not source or source_id is None:
        raise ValidationError("Service charges require a source type and source ID.")
    key=f"service:{source}:{source_id}"
    return generate_charge(rule=rule,generation_key=key,charge_date=service_date,description=description,amount=amount,season=season,notes=notes)
