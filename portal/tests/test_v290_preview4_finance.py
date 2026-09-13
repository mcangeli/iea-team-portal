from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class ArenaLinePreview4FinanceTests(SimpleTestCase):
    def test_base_loads_finance_presentation_layer(self):
        base = (Path(settings.BASE_DIR) / "templates/base.html").read_text()
        self.assertIn("css/finance-v290.css", base)

    def test_finance_layer_covers_core_surfaces(self):
        css = (Path(settings.BASE_DIR) / "static/css/finance-v290.css").read_text()

        for selector in (
            ".finance-stat-grid",
            ".finance-secondary-summary",
            ".finance-attention-grid",
            ".finance-account-grid",
            ".family-charge-card",
            ".family-ledger-lines",
            ".assistance-card",
        ):
            self.assertIn(selector, css)

    def test_family_account_finance_workflows_remain_available(self):
        family = (Path(settings.BASE_DIR) / "templates/portal/family_account.html").read_text()

        self.assertIn("Generate membership dues", family)
        self.assertIn("Record payment", family)
        self.assertIn("Add assistance", family)
        self.assertIn("Add service credit", family)
        self.assertIn("family_payment_delete", family)
        self.assertIn("assistance_claims", family)

    def test_receivables_and_dashboard_finance_hierarchy_remain_intact(self):
        dashboard = (Path(settings.BASE_DIR) / "templates/portal/finance_dashboard.html").read_text()
        receivables = (Path(settings.BASE_DIR) / "templates/portal/finance_receivables.html").read_text()

        self.assertIn("TREASURER WORKLIST", dashboard)
        self.assertIn("BUDGET VS ACTUAL", dashboard)
        self.assertIn("Recent transactions", dashboard)
        self.assertIn("Family receivables", receivables)
        self.assertIn("Outstanding", receivables)
