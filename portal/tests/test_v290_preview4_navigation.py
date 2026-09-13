from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class ArenaLinePreview4NavigationTests(SimpleTestCase):
    def test_base_loads_final_polish_layer(self):
        base = (Path(settings.BASE_DIR) / "templates/base.html").read_text()
        self.assertIn("css/final-polish-v290.css", base)

    def test_navigation_matches_module_registry_structure(self):
        base = (Path(settings.BASE_DIR) / "templates/base.html").read_text()

        self.assertIn('data-module="people"', base)
        self.assertIn('data-module="horses"', base)
        self.assertIn('data-module="competition_iea"', base)
        self.assertIn('data-module="operations"', base)
        self.assertIn('data-module="finance"', base)
        self.assertIn('data-module="communications"', base)

        self.assertIn('<summary>Finance</summary>', base)
        self.assertIn("finance_dashboard", base)
        self.assertIn("finance_receivables", base)
        self.assertIn("finance_dues_setup", base)
        self.assertIn("finance_reports", base)
        self.assertIn("fundraising_dashboard", base)
        self.assertIn("reimbursement_list", base)

        operations_start = base.index('<details class="nav-menu" data-module="operations">')
        operations_end = base.index('</details>', operations_start)
        operations_menu = base[operations_start:operations_end]
        self.assertNotIn("finance_dashboard", operations_menu)

    def test_manage_navigation_is_organization_administration(self):
        base = (Path(settings.BASE_DIR) / "templates/base.html").read_text()
        self.assertIn("Organization administration", base)
        for route_name in ("user_list", "season_setup", "team_branding", "audit_log"):
            self.assertIn(route_name, base)

    def test_final_polish_protects_mobile_navigation_and_focus(self):
        css = (Path(settings.BASE_DIR) / "static/css/final-polish-v290.css").read_text()
        self.assertIn(":focus-visible", css)
        self.assertIn(".main-nav.is-open", css)
        self.assertIn("overflow-y: auto", css)
        self.assertIn(".entry-table-wrap", css)
        self.assertIn("@media (max-width: 760px)", css)
