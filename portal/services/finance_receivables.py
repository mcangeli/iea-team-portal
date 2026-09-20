"""v3.5 receivables service boundary.

Keep receivable posting/allocation rules here so views, imports, exports and
future reconciliation integrations do not manipulate ledger rows directly.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from portal.models import FinancialTransaction

from portal.model_modules.finance import (
    ZERO,
    ReceivableAccount,
    ReceivableAllocation,
    ReceivableCharge,
    ReceivableCredit,
    ReceivablePayment,
)


def account_amount_due(account: ReceivableAccount) -> Decimal:
    return account.amount_due


def account_unapplied_payments(account: ReceivableAccount) -> Decimal:
    return account.unapplied_payment_total


def account_unapplied_credits(account: ReceivableAccount) -> Decimal:
    return account.unapplied_credit_total


def account_net_balance(account: ReceivableAccount) -> Decimal:
    return account.balance


def reconcile_legacy_account(account: ReceivableAccount) -> dict:
    """Compare migrated IEA charge balances with the legacy family ledger."""
    if not account.legacy_membership_id:
        return {"legacy_amount_due": ZERO, "receivable_amount_due": account.amount_due, "difference": account.amount_due}
    legacy_amount_due = sum((charge.balance for charge in account.legacy_membership.charges.all()), ZERO)
    receivable_amount_due = account.amount_due
    return {"legacy_amount_due": legacy_amount_due, "receivable_amount_due": receivable_amount_due, "difference": receivable_amount_due - legacy_amount_due}


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

    available = min(charge.balance, source.unapplied_amount)
    requested = available if amount is None else Decimal(amount)
    if requested <= ZERO or available <= ZERO:
        return None
    allocation_amount = min(requested, available)
    allocation = ReceivableAllocation(charge=charge, payment=payment, credit=credit, amount=allocation_amount, notes=notes)
    allocation.full_clean()
    allocation.save()
    return allocation


@transaction.atomic
def allocate_source_oldest(*, payment: ReceivablePayment | None = None,
                           credit: ReceivableCredit | None = None, notes: str = "") -> list[ReceivableAllocation]:
    """Apply an unapplied payment or credit to oldest outstanding posted charges."""
    if bool(payment) == bool(credit):
        raise ValidationError("Provide exactly one payment or credit source.")
    source=payment or credit
    if source.status!=source.Status.POSTED:
        raise ValidationError("Only posted sources may be allocated.")
    allocations=[]
    charges=source.account.charges.filter(status=ReceivableCharge.Status.POSTED).order_by("due_date","charge_date","id")
    for charge in charges:
        if source.unapplied_amount<=ZERO:
            break
        if charge.balance<=ZERO:
            continue
        allocation=allocate_source(charge=charge,payment=payment,credit=credit,notes=notes)
        if allocation is not None:
            allocations.append(allocation)
    return allocations


@transaction.atomic
def post_payment(*, account: ReceivableAccount, amount: Decimal, received_date,
                 charge: ReceivableCharge | None = None, **kwargs) -> ReceivablePayment:
    payment = ReceivablePayment(account=account, amount=amount, received_date=received_date, **kwargs)
    payment.full_clean()
    payment.save()
    if payment.deposit_account_id and payment.income_category_id and not payment.financial_transaction_id:
        transaction_row = FinancialTransaction(
            team=account.team,
            season=payment.season,
            transaction_date=payment.received_date,
            kind=FinancialTransaction.Kind.INCOME,
            account=payment.deposit_account,
            category=payment.income_category,
            amount=payment.amount,
            payee=account.name,
            description=f"Receivable payment — {account.name}",
            reference=payment.reference,
            notes=payment.notes,
        )
        transaction_row.full_clean()
        transaction_row.save()
        payment.financial_transaction=transaction_row
        payment.save(update_fields=["financial_transaction","updated_at"])
    if charge is not None:
        allocate_source(charge=charge, payment=payment)
    return payment


@transaction.atomic
def post_credit(*, account: ReceivableAccount, description: str, amount: Decimal,
                credit_date, charge: ReceivableCharge | None = None, **kwargs) -> ReceivableCredit:
    credit = ReceivableCredit(account=account, description=description, amount=amount, credit_date=credit_date, **kwargs)
    credit.full_clean()
    credit.save()
    if charge is not None:
        allocate_source(charge=charge, credit=credit)
    return credit


@transaction.atomic
def void_payment(*, payment: ReceivablePayment, user=None, reason: str = "") -> ReceivablePayment:
    """Void a receivable payment and its linked bookkeeping transaction together."""
    if payment.status != payment.Status.POSTED:
        raise ValidationError("Only posted payments may be voided.")
    if payment.allocations.filter(status=ReceivableAllocation.Status.POSTED).exists():
        raise ValidationError("Allocated payments must be unallocated before they can be voided.")
    tx = payment.financial_transaction
    if tx is not None:
        if tx.status != FinancialTransaction.Status.POSTED:
            raise ValidationError("Linked financial transaction is not posted.")
        tx.status = FinancialTransaction.Status.VOID
        tx.voided_at = timezone.now()
        tx.voided_by = user
        tx.void_reason = reason.strip()
        tx.save(update_fields=["status","voided_at","voided_by","void_reason","updated_at"])
    payment.status = payment.Status.VOID
    if reason.strip():
        payment.notes = (payment.notes + "\n" if payment.notes else "") + f"Void: {reason.strip()}"
    payment.save(update_fields=["status","notes","updated_at"])
    return payment
