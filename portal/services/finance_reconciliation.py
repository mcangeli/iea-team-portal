"""Candidate generation and explicit confirmation for staged bank reconciliation."""
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from portal.model_modules.finance import ImportedBankTransaction, ReconciliationMatch
from portal.models import FinancialTransaction

def _expected_kind(row):
    return FinancialTransaction.Kind.INCOME if row.direction==ImportedBankTransaction.Direction.CREDIT else FinancialTransaction.Kind.EXPENSE

def _candidate_score(row,tx):
    score=50;rationale=["amount"]
    days=abs((tx.transaction_date-row.transaction_date).days)
    if days==0:score+=30;rationale.append("same date")
    elif days<=2:score+=20;rationale.append(f"{days}d date")
    elif days<=5:score+=10;rationale.append(f"{days}d date")
    ref=(row.reference or row.external_id or "").strip().lower()
    if ref and ref in {(tx.reference or "").strip().lower(),(tx.description or "").strip().lower()}:
        score+=20;rationale.append("reference")
    elif row.description and tx.description and (row.description.lower() in tx.description.lower() or tx.description.lower() in row.description.lower()):
        score+=10;rationale.append("description")
    return min(score,100),", ".join(rationale)

@transaction.atomic
def generate_match_candidates(row,*,date_window_days=5):
    if row.status not in (ImportedBankTransaction.Status.STAGED,ImportedBankTransaction.Status.MATCHED):raise ValidationError("Only staged bank transactions can be matched.")
    start=row.transaction_date-timedelta(days=date_window_days);end=row.transaction_date+timedelta(days=date_window_days)
    candidates=FinancialTransaction.objects.filter(team=row.batch.team,account=row.batch.financial_account,status=FinancialTransaction.Status.POSTED,kind=_expected_kind(row),amount=row.amount,transaction_date__range=(start,end)).order_by("transaction_date","id")
    matches=[]
    for tx in candidates:
        score,rationale=_candidate_score(row,tx)
        match,_=ReconciliationMatch.objects.update_or_create(imported_transaction=row,financial_transaction=tx,defaults={"score":score,"rationale":rationale,"status":ReconciliationMatch.Status.SUGGESTED})
        matches.append(match)
    if matches and row.status==ImportedBankTransaction.Status.STAGED:
        row.status=ImportedBankTransaction.Status.MATCHED;row.save(update_fields=["status"])
    return sorted(matches,key=lambda m:(-m.score,m.financial_transaction.transaction_date,m.pk))

@transaction.atomic
def confirm_reconciliation(match):
    match=ReconciliationMatch.objects.select_for_update().select_related("imported_transaction__batch","financial_transaction").get(pk=match.pk)
    row=match.imported_transaction
    if match.status==ReconciliationMatch.Status.REJECTED:raise ValidationError("Rejected matches cannot be confirmed.")
    if row.matches.filter(status=ReconciliationMatch.Status.CONFIRMED).exclude(pk=match.pk).exists():raise ValidationError("This bank transaction is already reconciled.")
    if ReconciliationMatch.objects.filter(financial_transaction=match.financial_transaction,status=ReconciliationMatch.Status.CONFIRMED).exclude(pk=match.pk).exists():raise ValidationError("This ledger transaction is already reconciled to another bank transaction.")
    match.full_clean();match.status=ReconciliationMatch.Status.CONFIRMED;match.confirmed_at=timezone.now();match.save(update_fields=["status","confirmed_at"])
    row.status=ImportedBankTransaction.Status.RECONCILED;row.save(update_fields=["status"])
    row.matches.exclude(pk=match.pk).filter(status=ReconciliationMatch.Status.SUGGESTED).update(status=ReconciliationMatch.Status.REJECTED)
    return match
