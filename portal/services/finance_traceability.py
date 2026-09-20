"""Trace financial ledger entries back to ArenaLine operational sources."""
from dataclasses import dataclass

from portal.model_modules.finance import PayablePayment, ReceivablePayment, ReconciliationMatch


@dataclass(frozen=True)
class TransactionTrace:
    source_kind:str
    source_label:str
    source_object:object
    reconciliation_matches:tuple


def transaction_trace(transaction):
    source_kind="ledger";source_label="Direct ledger transaction";source_object=None
    try:
        source_object=transaction.receivable_payment
    except ReceivablePayment.DoesNotExist:
        pass
    if source_object is not None:
        source_kind="receivable_payment";source_label="Receivable payment"
    else:
        try:
            source_object=transaction.payable_payment
        except PayablePayment.DoesNotExist:
            pass
        if source_object is not None:
            source_kind="payable_payment";source_label="Payable payment"
    matches=tuple(transaction.bank_matches.filter(status=ReconciliationMatch.Status.CONFIRMED).select_related("imported_transaction__batch"))
    return TransactionTrace(source_kind,source_label,source_object,matches)
