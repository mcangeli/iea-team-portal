from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class ArenaLinePreview4PresentationTests(SimpleTestCase):
    def test_shared_presentation_contract_lives_in_arenaline_css(self):
        css = (Path(settings.BASE_DIR) / "static/css/arenaline-v290.css").read_text()

        self.assertIn("/* Preview 4: shared presentation contract. */", css)
        self.assertIn(".page-title,.page-intro{", css)
        self.assertIn(".section-head{", css)
        self.assertIn(".entry-table-wrap{", css)
        self.assertIn(".form-card{", css)
        self.assertIn(".dashboard-workspaces{", css)
        self.assertIn(".filter-tabs{", css)

    def test_dashboard_does_not_embed_workspace_presentation_css(self):
        dashboard = (Path(settings.BASE_DIR) / "templates/portal/dashboard.html").read_text()

        self.assertNotIn("<style>", dashboard)
        self.assertNotIn('class="dashboard-workspaces"', dashboard)
        self.assertNotIn('class="dashboard-workspace-link', dashboard)

    def test_representative_modules_use_shared_page_and_section_patterns(self):
        rider_list = (Path(settings.BASE_DIR) / "templates/portal/rider_list.html").read_text()
        finance = (Path(settings.BASE_DIR) / "templates/portal/finance_dashboard.html").read_text()

        self.assertIn('class="page-title"', rider_list)
        self.assertIn('class="section-head"', rider_list)
        self.assertIn('class="filter-tabs"', rider_list)

        self.assertIn('class="page-intro finance-intro"', finance)
        self.assertIn('class="section-head"', finance)
        self.assertIn('class="entry-table-wrap"', finance)
        self.assertIn('class="entry-table finance-table"', finance)
