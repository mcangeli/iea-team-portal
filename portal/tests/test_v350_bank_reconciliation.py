from datetime import date
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase
from portal.model_modules.finance import BankImportBatch, BankImportProfile, FinanceDomain, ImportedBankTransaction, ReconciliationMatch
from portal.models import FinancialAccount, FinancialCategory, FinancialTransaction, Team

class BankReconciliationFoundationTests(TestCase):
    def setUp(self):
        self.team=Team.objects.create(name="Reconciliation Barn");self.other=Team.objects.create(name="Other Barn")
        self.general=FinancialAccount.objects.create(team=self.team,name="General Checking",finance_domain=FinanceDomain.GENERAL)
        self.iea=FinancialAccount.objects.create(team=self.team,name="IEA Checking",finance_domain=FinanceDomain.IEA)
        self.category=FinancialCategory.objects.create(team=self.team,name="Income",kind=FinancialCategory.Kind.INCOME)

    def test_import_profile_is_bound_to_financial_account(self):
        profile=BankImportProfile(team=self.team,financial_account=self.general,name="Bank CSV",column_mapping={"date":"Date","amount":"Amount"})
        profile.full_clean();profile.save();self.assertEqual(profile.financial_account.finance_domain,FinanceDomain.GENERAL)

    def test_import_batch_rejects_domain_mismatch(self):
        batch=BankImportBatch(team=self.team,financial_account=self.iea,finance_domain=FinanceDomain.GENERAL,source_name="statement.csv",source_fingerprint="a"*64)
        with self.assertRaises(ValidationError):batch.full_clean()

    def test_imported_rows_are_staged_and_do_not_mutate_ledger(self):
        batch=BankImportBatch.objects.create(team=self.team,financial_account=self.general,finance_domain=FinanceDomain.GENERAL,source_name="statement.csv",source_fingerprint="b"*64)
        row=ImportedBankTransaction.objects.create(batch=batch,transaction_date=date(2026,9,1),amount=Decimal("125.00"),direction=ImportedBankTransaction.Direction.CREDIT,description="Deposit",row_fingerprint="c"*64)
        self.assertEqual(row.status,ImportedBankTransaction.Status.STAGED);self.assertEqual(FinancialTransaction.objects.count(),0)

    def test_reconciliation_match_must_use_imported_financial_account(self):
        batch=BankImportBatch.objects.create(team=self.team,financial_account=self.general,finance_domain=FinanceDomain.GENERAL,source_name="statement.csv",source_fingerprint="d"*64)
        row=ImportedBankTransaction.objects.create(batch=batch,transaction_date=date(2026,9,2),amount=Decimal("50.00"),direction=ImportedBankTransaction.Direction.CREDIT,description="Deposit",row_fingerprint="e"*64)
        tx=FinancialTransaction.objects.create(team=self.team,transaction_date=date(2026,9,2),kind=FinancialTransaction.Kind.INCOME,account=self.iea,category=self.category,amount=Decimal("50.00"),description="Wrong domain/account")
        match=ReconciliationMatch(imported_transaction=row,financial_transaction=tx,score=100)
        with self.assertRaises(ValidationError):match.full_clean()
