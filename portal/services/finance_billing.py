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
