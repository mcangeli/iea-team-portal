from datetime import date
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase
from portal.model_modules.finance import BankImportBatch, FinanceDomain, ImportedBankTransaction, ReconciliationMatch
from portal.models import FinancialAccount, FinancialCategory, FinancialTransaction, Team
from portal.services.finance_reconciliation import confirm_reconciliation, generate_match_candidates

class ReconciliationMatchingTests(TestCase):
    def setUp(self):
        self.team=Team.objects.create(name="Match Barn");self.account=FinancialAccount.objects.create(team=self.team,name="Checking",finance_domain=FinanceDomain.GENERAL);self.other=FinancialAccount.objects.create(team=self.team,name="Savings",finance_domain=FinanceDomain.GENERAL);self.category=FinancialCategory.objects.create(team=self.team,name="Both",kind=FinancialCategory.Kind.BOTH)
        self.batch=BankImportBatch.objects.create(team=self.team,financial_account=self.account,finance_domain=FinanceDomain.GENERAL,source_name="bank.csv",source_fingerprint="f"*64)
    def _row(self,amount="100.00",direction=ImportedBankTransaction.Direction.CREDIT,day=10,reference="REF-1"):
        return ImportedBankTransaction.objects.create(batch=self.batch,transaction_date=date(2026,9,day),amount=Decimal(amount),direction=direction,description="Client deposit",reference=reference,row_fingerprint=(str(day)+direction+"x"*64)[:64])
    def _tx(self,account=None,amount="100.00",kind=FinancialTransaction.Kind.INCOME,day=10,reference="REF-1"):
        return FinancialTransaction.objects.create(team=self.team,transaction_date=date(2026,9,day),kind=kind,account=account or self.account,category=self.category,amount=Decimal(amount),description="Client deposit",reference=reference)
    def test_candidates_require_same_account_amount_and_direction(self):
        row=self._row();correct=self._tx();self._tx(account=self.other);self._tx(amount="99.00");self._tx(kind=FinancialTransaction.Kind.EXPENSE)
        matches=generate_match_candidates(row);self.assertEqual([m.financial_transaction_id for m in matches],[correct.pk])
    def test_same_date_reference_match_scores_highest(self):
        row=self._row();best=self._tx();self._tx(day=12,reference="OTHER")
        matches=generate_match_candidates(row);self.assertEqual(matches[0].financial_transaction_id,best.pk);self.assertEqual(matches[0].score,100)
    def test_candidate_generation_does_not_reconcile(self):
        row=self._row();self._tx();generate_match_candidates(row);row.refresh_from_db();self.assertEqual(row.status,ImportedBankTransaction.Status.MATCHED);self.assertFalse(ReconciliationMatch.objects.filter(status=ReconciliationMatch.Status.CONFIRMED).exists())
    def test_confirmation_reconciles_one_to_one(self):
        row=self._row();tx=self._tx();match=generate_match_candidates(row)[0];confirm_reconciliation(match);row.refresh_from_db();match.refresh_from_db();self.assertEqual(row.status,ImportedBankTransaction.Status.RECONCILED);self.assertEqual(match.status,ReconciliationMatch.Status.CONFIRMED)
        row2=self._row(day=11,reference="REF-2");match2=ReconciliationMatch.objects.create(imported_transaction=row2,financial_transaction=tx,score=50)
        with self.assertRaises(ValidationError):confirm_reconciliation(match2)
