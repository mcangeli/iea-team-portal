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
        self.user.is_superuser=True;self.user.is_staff=True;self.user.save(update_fields=["is_superuser","is_staff"])\n        profile=self.user.profile;profile.team=self.team;profile.save(update_fields=["team"])
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

    def _row_with_match(self, suffix="x"):
        batch=BankImportBatch.objects.create(team=self.team,financial_account=self.account,finance_domain=FinanceDomain.GENERAL,source_name=f"{suffix}.csv",source_fingerprint=suffix*64)
        row=ImportedBankTransaction.objects.create(batch=batch,transaction_date=date(2026,9,17),amount=Decimal("42.00"),direction=ImportedBankTransaction.Direction.CREDIT,description="Deposit",row_fingerprint=(suffix.upper())*64)
        category=FinancialCategory.objects.filter(team=self.team,name="Income").first() or FinancialCategory.objects.create(team=self.team,name="Income",kind=FinancialCategory.Kind.INCOME)
        tx=FinancialTransaction.objects.create(team=self.team,transaction_date=row.transaction_date,kind=FinancialTransaction.Kind.INCOME,account=self.account,category=category,amount=row.amount,description="Deposit")
        match=ReconciliationMatch.objects.create(imported_transaction=row,financial_transaction=tx,score=80)
        return batch,row,tx,match

    def test_reconciliation_actions_are_post_only(self):
        batch,row,tx,match=self._row_with_match("p")
        self.client.force_login(self.user)
        urls=[reverse("finance_bank_generate_candidates",args=[batch.pk,row.pk]),reverse("finance_bank_confirm_match",args=[batch.pk,row.pk,match.pk]),reverse("finance_bank_ignore_row",args=[batch.pk,row.pk]),reverse("finance_bank_complete_review",args=[batch.pk])]
        for url in urls:self.assertEqual(self.client.get(url).status_code,403)
        row.refresh_from_db();match.refresh_from_db();tx.refresh_from_db()
        self.assertEqual(row.status,ImportedBankTransaction.Status.STAGED);self.assertEqual(match.status,ReconciliationMatch.Status.SUGGESTED);self.assertEqual(tx.status,FinancialTransaction.Status.POSTED)

    def test_confirm_match_post_reconciles_without_mutating_ledger(self):
        batch,row,tx,match=self._row_with_match("c");before=(tx.amount,tx.description,tx.status)
        self.client.force_login(self.user)
        response=self.client.post(reverse("finance_bank_confirm_match",args=[batch.pk,row.pk,match.pk]))
        self.assertEqual(response.status_code,302)
        row.refresh_from_db();match.refresh_from_db();tx.refresh_from_db()
        self.assertEqual(row.status,ImportedBankTransaction.Status.RECONCILED);self.assertEqual(match.status,ReconciliationMatch.Status.CONFIRMED);self.assertEqual((tx.amount,tx.description,tx.status),before)

    def test_ignore_post_does_not_mutate_ledger(self):
        batch,row,tx,match=self._row_with_match("g");before=(tx.amount,tx.description,tx.status)
        self.client.force_login(self.user)
        response=self.client.post(reverse("finance_bank_ignore_row",args=[batch.pk,row.pk]))
        self.assertEqual(response.status_code,302)
        row.refresh_from_db();match.refresh_from_db();tx.refresh_from_db();batch.refresh_from_db()
        self.assertEqual(row.status,ImportedBankTransaction.Status.IGNORED);self.assertEqual(match.status,ReconciliationMatch.Status.REJECTED);self.assertEqual((tx.amount,tx.description,tx.status),before);self.assertEqual(batch.status,BankImportBatch.Status.COMPLETED)

    def test_complete_review_refuses_unresolved_rows(self):
        batch,row,tx,match=self._row_with_match("q")
        self.client.force_login(self.user)
        self.client.post(reverse("finance_bank_complete_review",args=[batch.pk]))
        batch.refresh_from_db();self.assertEqual(batch.status,BankImportBatch.Status.REVIEWED)

    def test_iea_treasurer_cannot_access_general_reconciliation_batch(self):
        from portal.model_modules.capabilities import OrganizationCapabilityAssignment
        from portal.model_modules.people import Person
        from portal.models import UserProfile
        user=get_user_model().objects.create_user(username="iea-bank",password="pass")
        profile=user.profile;profile.team=self.team;profile.role=UserProfile.Role.PARENT;profile.save(update_fields=["team","role"])
        person=Person.objects.create(team=self.team,user=user,first_name="IEA",last_name="Treasurer")
        OrganizationCapabilityAssignment.objects.create(team=self.team,person=person,capability=OrganizationCapabilityAssignment.Capability.MANAGE_IEA_FINANCE)
        batch,row,tx,match=self._row_with_match("d")
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("finance_bank_import_batch",args=[batch.pk])).status_code,403)
        self.assertEqual(self.client.post(reverse("finance_bank_ignore_row",args=[batch.pk,row.pk])).status_code,403)
        self.assertEqual(self.client.post(reverse("finance_bank_confirm_match",args=[batch.pk,row.pk,match.pk])).status_code,403)
        row.refresh_from_db();match.refresh_from_db();self.assertEqual(row.status,ImportedBankTransaction.Status.STAGED);self.assertEqual(match.status,ReconciliationMatch.Status.SUGGESTED)
