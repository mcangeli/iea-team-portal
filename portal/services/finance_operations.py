"""Authorized write-side operations for the ArenaLine v3.5 receivables ledger.

Every mutation resolves the receivable account through finance_access first.
That keeps General/IEA authorization identical for views, future APIs and imports.
"""
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from portal.model_modules.finance import ReceivableCharge
from portal.services.finance_access import finance_account_for_user
from portal.services.finance_receivables import allocate_source, post_credit, post_payment


def _authorized_account(user, account_id, team=None):
    account = finance_account_for_user(user, account_id, team)
    if account is None:
        raise PermissionDenied
    return account


def _posted_charge(account, charge_id):
    try:
        charge = account.charges.get(pk=charge_id, status=ReceivableCharge.Status.POSTED)
    except ReceivableCharge.DoesNotExist as exc:
        raise ValidationError("Charge is not available on this receivable account.") from exc
    return charge


@transaction.atomic
def create_charge_for_user(user, account_id, *, description, amount, charge_date,
                           due_date=None, charge_type="", season=None, notes="", team=None):
    account = _authorized_account(user, account_id, team)
    charge = ReceivableCharge(
        account=account,
        description=description.strip(),
        amount=Decimal(amount),
        charge_date=charge_date,
        due_date=due_date,
        charge_type=charge_type.strip(),
        season=season,
        notes=notes.strip(),
    )
    charge.full_clean()
    charge.save()
    return charge


@transaction.atomic
def post_payment_for_user(user, account_id, *, amount, received_date, charge_id=None,
                          method="", reference="", notes="", deposit_account=None,
                          income_category=None, season=None, team=None):
    account = _authorized_account(user, account_id, team)
    charge = _posted_charge(account, charge_id) if charge_id else None
    return post_payment(
        account=account,
        amount=Decimal(amount),
        received_date=received_date,
        charge=charge,
        method=method.strip(),
        reference=reference.strip(),
        notes=notes.strip(),
        deposit_account=deposit_account,
        income_category=income_category,
        season=season,
    )


@transaction.atomic
def post_credit_for_user(user, account_id, *, description, amount, credit_date,
                         charge_id=None, credit_type="", notes="", season=None, team=None):
    account = _authorized_account(user, account_id, team)
    charge = _posted_charge(account, charge_id) if charge_id else None
    return post_credit(
        account=account,
        description=description.strip(),
        amount=Decimal(amount),
        credit_date=credit_date,
        charge=charge,
        credit_type=credit_type.strip(),
        notes=notes.strip(),
        season=season,
    )


@transaction.atomic
def allocate_payment_for_user(user, account_id, *, payment_id, charge_id, amount=None,
                              notes="", team=None):
    account = _authorized_account(user, account_id, team)
    charge = _posted_charge(account, charge_id)
    try:
        payment = account.payments.get(pk=payment_id, status=account.payments.model.Status.POSTED)
    except account.payments.model.DoesNotExist as exc:
        raise ValidationError("Payment is not available on this receivable account.") from exc
    return allocate_source(charge=charge, payment=payment, amount=amount, notes=notes.strip())


@transaction.atomic
def allocate_credit_for_user(user, account_id, *, credit_id, charge_id, amount=None,
                             notes="", team=None):
    account = _authorized_account(user, account_id, team)
    charge = _posted_charge(account, charge_id)
    try:
        credit = account.credits.get(pk=credit_id, status=account.credits.model.Status.POSTED)
    except account.credits.model.DoesNotExist as exc:
        raise ValidationError("Credit is not available on this receivable account.") from exc
    return allocate_source(charge=charge, credit=credit, amount=amount, notes=notes.strip())
