"""v3.7 accounts payable service boundary."""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from portal.model_modules.finance import PayableObligation, PayablePayment, PayableParty, ZERO
from portal.models import FinancialTransaction


@transaction.atomic
def create_obligation(*, party: PayableParty, expense_category, description: str, amount: Decimal,
                      obligation_date, due_date=None, season=None, reference="", notes=""):
    obligation = PayableObligation(
        party=party, expense_category=expense_category, description=description.strip(),
        amount=Decimal(amount), obligation_date=obligation_date, due_date=due_date,
        season=season, reference=reference.strip(), notes=notes.strip(),
    )
    obligation.full_clean()
    obligation.save()
    return obligation


@transaction.atomic
def post_payable_payment(*, obligation: PayableObligation, amount: Decimal, paid_date,
                         payment_account, method="", reference="", notes=""):
    if obligation.status != PayableObligation.Status.OPEN:
        raise ValidationError("Only open payable obligations may be paid.")
    payment = PayablePayment(
        obligation=obligation, amount=Decimal(amount), paid_date=paid_date,
        payment_account=payment_account, method=method.strip(), reference=reference.strip(),
        notes=notes.strip(),
    )
    payment.full_clean()
    payment.save()

    ledger = FinancialTransaction(
        team=obligation.party.team,
        season=obligation.season,
        transaction_date=paid_date,
        kind=FinancialTransaction.Kind.EXPENSE,
        account=payment_account,
        category=obligation.expense_category,
        amount=payment.amount,
        payee=obligation.party.name,
        description=obligation.description,
        reference=payment.reference or obligation.reference,
        notes=payment.notes,
    )
    ledger.full_clean()
    ledger.save()
    payment.financial_transaction = ledger
    payment.save(update_fields=["financial_transaction", "updated_at"])
    return payment


@transaction.atomic
def void_payable_payment(*, payment: PayablePayment, user=None, reason=""):
    if payment.status != PayablePayment.Status.POSTED:
        raise ValidationError("Only posted payable payments may be voided.")
    ledger = payment.financial_transaction
    if ledger is not None:
        if ledger.status != FinancialTransaction.Status.POSTED:
            raise ValidationError("Linked financial transaction is not posted.")
        ledger.status = FinancialTransaction.Status.VOID
        ledger.voided_at = timezone.now()
        ledger.voided_by = user
        ledger.void_reason = reason.strip()
        ledger.save(update_fields=["status", "voided_at", "voided_by", "void_reason", "updated_at"])
    payment.status = PayablePayment.Status.VOID
    if reason.strip():
        payment.notes = (payment.notes + "\n" if payment.notes else "") + f"Void: {reason.strip()}"
    payment.save(update_fields=["status", "notes", "updated_at"])
    return payment
