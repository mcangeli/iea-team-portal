"""Earned receivable credits for ArenaLine v3.7.1."""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from portal.model_modules.finance import ReceivableCredit, ReceivableCreditRule


def earned_credit_key(source_type, source_id):
    source=(source_type or "").strip().lower()
    if not source or source_id is None or str(source_id).strip()=="":
        raise ValidationError("Earned credits require a source type and source ID.")
    return f"earned:{source}:{source_id}"


@transaction.atomic
def generate_earned_credit(*,account,source_type,source_id,credit_date,description,amount,
                           credit_type="",season=None,notes="",generation_key=None,credit_rule=None):
    """Post an auditable, retry-safe credit without changing the original charge."""
    if credit_rule is not None and (credit_rule.team_id!=account.team_id or credit_rule.finance_domain!=account.finance_domain):
        raise ValidationError("Credit rule and receivable account must share an organization and finance domain.")
    if credit_rule is not None and (source_type or "").strip().lower()!=credit_rule.source_type:
        raise ValidationError("Earned credit source type must match the supplied credit rule.")
    if season is not None and season.team_id!=account.team_id:
        raise ValidationError("Credit season must belong to the account organization.")
    value=Decimal(amount)
    if value<=0:
        raise ValidationError("Earned credit amount must be greater than zero.")
    key=generation_key or earned_credit_key(source_type,source_id)
    existing=ReceivableCredit.objects.filter(account=account,generation_key=key).first()
    if existing:
        return existing,False
    credit=ReceivableCredit(
        account=account,credit_rule=credit_rule,generation_key=key,source_type=(source_type or "").strip().lower(),
        source_id=str(source_id).strip(),season=season,description=description.strip(),
        amount=value,credit_date=credit_date,credit_type=credit_type.strip(),notes=notes.strip(),
    )
    credit.full_clean()
    try:
        with transaction.atomic():
            credit.save()
    except IntegrityError:
        existing=ReceivableCredit.objects.filter(account=account,generation_key=key).first()
        if existing:
            return existing,False
        raise
    return credit,True


def calculate_earned_credit(rule: ReceivableCreditRule, *, quantity=None):
    if not rule.active:
        raise ValidationError("Inactive credit rules cannot generate credits.")
    if rule.calculation==ReceivableCreditRule.Calculation.FIXED:
        return rule.rate
    if quantity is None:
        raise ValidationError("Quantity-based credit rules require a quantity.")
    qty=Decimal(quantity)
    if qty<=0:
        raise ValidationError("Credit quantity must be greater than zero.")
    return (rule.rate*qty).quantize(Decimal("0.01"))


@transaction.atomic
def generate_rule_credit(*,rule:ReceivableCreditRule,account,source_id,credit_date,quantity=None,
                         description=None,season=None,notes=""):
    if account.team_id!=rule.team_id or account.finance_domain!=rule.finance_domain:
        raise ValidationError("Credit rule and receivable account must share an organization and finance domain.")
    amount=calculate_earned_credit(rule,quantity=quantity)
    key=f"credit-rule:{rule.pk}:{earned_credit_key(rule.source_type,source_id)}"
    return generate_earned_credit(
        account=account,source_type=rule.source_type,source_id=source_id,
        credit_date=credit_date,description=(description or rule.name),amount=amount,
        credit_type=rule.credit_type,season=season,notes=notes,generation_key=key,credit_rule=rule,
    )
