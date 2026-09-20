"""Earned receivable credits for ArenaLine v3.7.1."""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from portal.model_modules.finance import ReceivableCredit


def earned_credit_key(source_type, source_id):
    source=(source_type or "").strip().lower()
    if not source or source_id is None or str(source_id).strip()=="":
        raise ValidationError("Earned credits require a source type and source ID.")
    return f"earned:{source}:{source_id}"


@transaction.atomic
def generate_earned_credit(*,account,source_type,source_id,credit_date,description,amount,
                           credit_type="",season=None,notes=""):
    """Post an auditable, retry-safe credit without changing the original charge."""
    if season is not None and season.team_id!=account.team_id:
        raise ValidationError("Credit season must belong to the account organization.")
    value=Decimal(amount)
    if value<=0:
        raise ValidationError("Earned credit amount must be greater than zero.")
    key=earned_credit_key(source_type,source_id)
    existing=ReceivableCredit.objects.filter(account=account,generation_key=key).first()
    if existing:
        return existing,False
    credit=ReceivableCredit(
        account=account,generation_key=key,source_type=(source_type or "").strip().lower(),
        source_id=str(source_id).strip(),season=season,description=description.strip(),
        amount=value,credit_date=credit_date,credit_type=credit_type.strip(),notes=notes.strip(),
    )
    credit.full_clean();credit.save()
    return credit,True
