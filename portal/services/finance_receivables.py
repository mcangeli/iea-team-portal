"""v3.5 receivables service boundary.

Keep receivable posting/allocation rules here so views, imports, exports and
future reconciliation integrations do not manipulate ledger rows directly.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from portal.model_modules.finance import (
    ZERO,
    ReceivableAccount,
    ReceivableAllocation,
    ReceivableCharge,
    ReceivableCredit,
    ReceivablePayment,
)


def account_amount_due(account: ReceivableAccount) -> Decimal:
    """Outstanding posted charge balances; never reduced below zero."""
    return sum((charge.balance for charge in account.charges.all()), ZERO)


def account_unapplied_payments(account: ReceivableAccount) -> Decimal:
    return sum((payment.unapplied_amount for payment in account.payments.all()), ZERO)


def account_unapplied_credits(account: ReceivableAccount) -> Decimal:
    return sum((credit.unapplied_amount for credit in account.credits.all()), ZERO)


def account_net_balance(account: ReceivableAccount) -> Decimal:
    """Customer net position: positive is due, negative is available credit."""
    return account_amount_due(account) - account_unapplied_payments(account) - account_unapplied_credits(account)


def _remaining_charge_amount(charge: ReceivableCharge) -> Decimal:
    return max(charge.balance, ZERO)


def _remaining_source_amount(source) -> Decimal:
    return max(source.unapplied_amount, ZERO)


@transaction.atomic
def allocate_source(*, charge: ReceivableCharge, payment: ReceivablePayment | None = None,
                    credit: ReceivableCredit | None = None, amount: Decimal | None = None,
                    notes: str = "") -> ReceivableAllocation | None:
    """Safely allocate a payment/credit, leaving any excess unapplied."""
    if bool(payment) == bool(credit):
        raise ValidationError("Provide exactly one payment or credit source.")
    source = payment or credit
    if source.account_id != charge.account_id:
        raise ValidationError("Allocation source and charge must belong to the same receivable account.")
    if source.account.finance_domain != charge.account.finance_domain:
        raise ValidationError("Allocation source and charge must belong to the same finance domain.")
    if source.status != source.Status.POSTED or charge.status != charge.Status.POSTED:
        raise ValidationError("Only posted sources may be allocated to posted charges.")

    available = min(_remaining_charge_amount(charge), _remaining_source_amount(source))
    requested = available if amount is None else Decimal(amount)
    if requested <= ZERO:
        return None
    allocation_amount = min(requested, available)
    if allocation_amount <= ZERO:
        return None

    allocation = ReceivableAllocation(
        charge=charge,
        payment=payment,
        credit=credit,
        amount=allocation_amount,
        notes=notes,
    )
    allocation.full_clean()
    allocation.save()
    return allocation


@transaction.atomic
def post_payment(*, account: ReceivableAccount, amount: Decimal, received_date,
                 charge: ReceivableCharge | None = None, **kwargs) -> ReceivablePayment:
    payment = ReceivablePayment(
        account=account,
        amount=amount,
        received_date=received_date,
        **kwargs,
    )
    payment.full_clean()
    payment.save()
    if charge is not None:
        allocate_source(charge=charge, payment=payment)
    return payment


@transaction.atomic
def post_credit(*, account: ReceivableAccount, description: str, amount: Decimal,
                credit_date, charge: ReceivableCharge | None = None, **kwargs) -> ReceivableCredit:
    credit = ReceivableCredit(
        account=account,
        description=description,
        amount=amount,
        credit_date=credit_date,
        **kwargs,
    )
    credit.full_clean()
    credit.save()
    if charge is not None:
        allocate_source(charge=charge, credit=credit)
    return credit
