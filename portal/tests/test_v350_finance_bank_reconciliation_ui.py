from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from portal.model_modules.finance import BankImportBatch, FinanceDomain
from portal.models import FinancialAccount, Team

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
