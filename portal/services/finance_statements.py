"""Account-history and statement projection services for ArenaLine v3.5.

This module is deliberately read-only. It projects the receivables ledger into
chronological activity and statement snapshots while requiring callers to enter
through the finance authorization boundary.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from portal.model_modules.finance import ZERO
from portal.services.finance_access import finance_account_for_user


@dataclass(frozen=True)
class AccountActivityRow:
    date: date
    kind: str
    description: str
    amount: Decimal
    balance: Decimal
    source_id: int


@dataclass(frozen=True)
class AccountStatement:
    account: object
    start_date: date
    end_date: date
    opening_balance: Decimal
    closing_balance: Decimal
    charges: Decimal
    credits: Decimal
    payments: Decimal
    activity: tuple
    amount_due: Decimal
    overdue_amount: Decimal
    unapplied_payments: Decimal
    unapplied_credits: Decimal


def _raw_activity(account):
    rows = []
    for charge in account.charges.all():
        if charge.status == charge.Status.POSTED:
            rows.append((charge.charge_date, 0, charge.pk, "charge", charge.description, charge.amount))
    for credit in account.credits.all():
        if credit.status == credit.Status.POSTED:
            rows.append((credit.credit_date, 1, credit.pk, "credit", credit.description, -credit.amount))
    for payment in account.payments.all():
        if payment.status == payment.Status.POSTED:
            description = payment.reference.strip() if payment.reference else "Payment"
            rows.append((payment.received_date, 2, payment.pk, "payment", description, -payment.amount))
    return sorted(rows, key=lambda row: (row[0], row[1], row[2]))


def account_activity(account, *, start_date=None, end_date=None):
    """Return chronological posted ledger activity with a running net balance."""
    running = ZERO
    result = []
    for activity_date, _sort, source_id, kind, description, signed_amount in _raw_activity(account):
        running += signed_amount
        if start_date and activity_date < start_date:
            continue
        if end_date and activity_date > end_date:
            continue
        result.append(AccountActivityRow(
            date=activity_date,
            kind=kind,
            description=description,
            amount=abs(signed_amount),
            balance=running,
            source_id=source_id,
        ))
    return tuple(result)


def statement_for_account(account, *, start_date, end_date, as_of=None):
    if end_date < start_date:
        raise ValueError("Statement end date cannot be before start date.")

    opening = ZERO
    charges = ZERO
    credits = ZERO
    payments = ZERO
    running = ZERO
    rows = []

    for activity_date, _sort, source_id, kind, description, signed_amount in _raw_activity(account):
        if activity_date < start_date:
            opening += signed_amount
            continue
        if activity_date > end_date:
            continue
        running = opening if not rows else rows[-1].balance
        running += signed_amount
        if kind == "charge":
            charges += signed_amount
        elif kind == "credit":
            credits += abs(signed_amount)
        else:
            payments += abs(signed_amount)
        rows.append(AccountActivityRow(
            date=activity_date,
            kind=kind,
            description=description,
            amount=abs(signed_amount),
            balance=running,
            source_id=source_id,
        ))

    closing = rows[-1].balance if rows else opening
    as_of = as_of or end_date
    posted_charges = account.charges.filter(status=account.charges.model.Status.POSTED)
    amount_due = sum((charge.balance for charge in posted_charges if charge.balance > ZERO), ZERO)
    overdue_amount = sum((charge.balance for charge in posted_charges if charge.balance > ZERO and charge.due_date and charge.due_date < as_of), ZERO)
    return AccountStatement(
        account=account,
        start_date=start_date,
        end_date=end_date,
        opening_balance=opening,
        closing_balance=closing,
        charges=charges,
        credits=credits,
        payments=payments,
        activity=tuple(rows),
        amount_due=amount_due,
        overdue_amount=overdue_amount,
        unapplied_payments=account.unapplied_payment_total,
        unapplied_credits=account.unapplied_credit_total,
    )


def statement_for_user(user, account_id, *, start_date, end_date, team=None):
    """Authorized statement entry point; inaccessible accounts return None."""
    account = finance_account_for_user(user, account_id, team)
    if account is None:
        return None
    return statement_for_account(account, start_date=start_date, end_date=end_date)
