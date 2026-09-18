from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from portal.model_modules.finance import BankImportBatch, FinanceDomain, ImportedBankTransaction, ReconciliationMatch
from portal.models import FinancialAccount, FinancialCategory, FinancialTransaction, Team
from datetime import date
from decimal import Decimal

class BankReconciliationWorkspaceTests(TestCase):
    def setUp(self):
        self.team=Team.objects.create(name="UI Barn")
        self.user=get_user_model().objects.create_user(username="financeadmin",password="testpass")
        self.user.is_superuser=True;self.user.is_staff=True;self.user.save(update_fields=["is_superuser","is_staff"])
        self.account=FinancialAccount.objects.create(team=self.team,name="Operating",finance_domain=FinanceDomain.GENERAL)
    def test_reconciliation_routes_resolve(self):
        self.assertEqual(reverse("finance_bank_reconciliation"),"/finance/workspace/reconciliation/")
        self.assertEqual(reverse("finance_bank_import_mapping"),"/finance/workspace/reconciliation/mapping/")
    def test_batch_review_is_domain_scoped(self):
        batch=BankImportBatch.objects.create(team=self.team,financial_account=self.account,finance_domain=FinanceDomain.GENERAL,source_name="statement.csv",source_fingerprint="u"*64)
        self.assertIn(str(batch.pk),reverse("finance_bank_import_batch",args=[batch.pk]))

    def test_candidate_and_confirmation_routes_resolve(self):
        row=ImportedBankTransaction.objects.create(batch=BankImportBatch.objects.create(team=self.team,financial_account=self.account,finance_domain=FinanceDomain.GENERAL,source_name="match.csv",source_fingerprint="m"*64),transaction_date=date(2026,9,17),amount=Decimal("42.00"),direction=ImportedBankTransaction.Direction.CREDIT,description="Deposit",row_fingerprint="r"*64)
        category=FinancialCategory.objects.create(team=self.team,name="Income",kind=FinancialCategory.Kind.INCOME)
        tx=FinancialTransaction.objects.create(team=self.team,transaction_date=row.transaction_date,kind=FinancialTransaction.Kind.INCOME,account=self.account,category=category,amount=row.amount,description="Deposit")
        match=ReconciliationMatch.objects.create(imported_transaction=row,financial_transaction=tx,score=80)
        self.assertIn("/candidates/",reverse("finance_bank_generate_candidates",args=[row.batch_id,row.pk]))
        self.assertIn("/confirm/",reverse("finance_bank_confirm_match",args=[row.batch_id,row.pk,match.pk]))

    def test_unmatched_review_routes_resolve(self):
        batch=BankImportBatch.objects.create(team=self.team,financial_account=self.account,finance_domain=FinanceDomain.GENERAL,source_name="review.csv",source_fingerprint="v"*64)
        row=ImportedBankTransaction.objects.create(batch=batch,transaction_date=date(2026,9,17),amount=Decimal("25.00"),direction=ImportedBankTransaction.Direction.DEBIT,description="Fee",row_fingerprint="i"*64)
        self.assertIn("/ignore/",reverse("finance_bank_ignore_row",args=[batch.pk,row.pk]))
        self.assertIn("/complete/",reverse("finance_bank_complete_review",args=[batch.pk]))
