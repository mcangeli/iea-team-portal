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
    score=50;rationale=["exact amount"];days=abs((tx.transaction_date-row.transaction_date).days)
    if days==0:score+=30;rationale.append("same date")
    elif days<=2:score+=20;rationale.append(f"{days}-day date difference")
    elif days<=5:score+=10;rationale.append(f"{days}-day date difference")
    ref=(row.reference or row.external_id or "").strip().lower();tx_ref=(tx.reference or "").strip().lower()
    if ref and tx_ref and ref==tx_ref:score+=20;rationale.append("exact reference")
    else:
        bank=(row.description or "").lower();ledger=" ".join([tx.description or "",tx.payee or ""]).lower()
        tokens={t for t in bank.replace("-"," ").split() if len(t)>=4}
        if tokens and any(t in ledger for t in tokens):score+=5;rationale.append("description/payee similarity")
    return min(score,100),", ".join(rationale)

@transaction.atomic
def generate_match_candidates(row,*,date_window_days=5):
    row=ImportedBankTransaction.objects.select_for_update().select_related("batch__financial_account","batch__team").get(pk=row.pk)
    if row.status not in (ImportedBankTransaction.Status.STAGED,ImportedBankTransaction.Status.MATCHED):raise ValidationError("Only staged or matched bank transactions can generate candidates.")
    start=row.transaction_date-timedelta(days=date_window_days);end=row.transaction_date+timedelta(days=date_window_days)
    candidates=FinancialTransaction.objects.filter(team=row.batch.team,account=row.batch.financial_account,status=FinancialTransaction.Status.POSTED,kind=_expected_kind(row),amount=row.amount,transaction_date__range=(start,end)).order_by("transaction_date","id")
    candidate_ids=[];matches=[]
    for tx in candidates:
        score,rationale=_candidate_score(row,tx)
        match,_=ReconciliationMatch.objects.update_or_create(imported_transaction=row,financial_transaction=tx,defaults={"score":score,"rationale":rationale,"status":ReconciliationMatch.Status.SUGGESTED,"confirmed_at":None})
        candidate_ids.append(tx.pk);matches.append(match)
    row.matches.filter(status=ReconciliationMatch.Status.SUGGESTED).exclude(financial_transaction_id__in=candidate_ids).update(status=ReconciliationMatch.Status.REJECTED)
    target_status=ImportedBankTransaction.Status.MATCHED if matches else ImportedBankTransaction.Status.STAGED
    if row.status!=target_status:row.status=target_status;row.save(update_fields=["status"])
    return sorted(matches,key=lambda m:(-m.score,m.financial_transaction.transaction_date,m.pk))

@transaction.atomic
def confirm_reconciliation(match):
    match=ReconciliationMatch.objects.select_for_update().select_related("imported_transaction__batch__financial_account","financial_transaction").get(pk=match.pk);row=match.imported_transaction;tx=match.financial_transaction
    if match.status==ReconciliationMatch.Status.REJECTED:raise ValidationError("Rejected matches cannot be confirmed.")
    if row.status==ImportedBankTransaction.Status.RECONCILED and match.status!=ReconciliationMatch.Status.CONFIRMED:raise ValidationError("This bank transaction is already reconciled.")
    if tx.status!=FinancialTransaction.Status.POSTED:raise ValidationError("Only posted ledger transactions can be reconciled.")
    if tx.team_id!=row.batch.team_id or tx.account_id!=row.batch.financial_account_id or tx.kind!=_expected_kind(row) or tx.amount!=row.amount:raise ValidationError("The selected ledger transaction no longer matches this bank transaction.")
    if row.matches.filter(status=ReconciliationMatch.Status.CONFIRMED).exclude(pk=match.pk).exists():raise ValidationError("This bank transaction is already reconciled.")
    if ReconciliationMatch.objects.filter(financial_transaction=tx,status=ReconciliationMatch.Status.CONFIRMED).exclude(pk=match.pk).exists():raise ValidationError("This ledger transaction is already reconciled to another bank transaction.")
    match.full_clean();match.status=ReconciliationMatch.Status.CONFIRMED;match.confirmed_at=timezone.now();match.save(update_fields=["status","confirmed_at"])
    if row.status!=ImportedBankTransaction.Status.RECONCILED:row.status=ImportedBankTransaction.Status.RECONCILED;row.save(update_fields=["status"])
    row.matches.exclude(pk=match.pk).filter(status=ReconciliationMatch.Status.SUGGESTED).update(status=ReconciliationMatch.Status.REJECTED)
    return match
