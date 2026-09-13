from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class ArenaLinePreview4DashboardTests(SimpleTestCase):
    def test_shared_dashboard_stylesheet_is_loaded_from_base(self):
        base = (Path(settings.BASE_DIR) / "templates/base.html").read_text()

        self.assertIn("css/dashboard-v290.css", base)

    def test_dashboard_templates_do_not_keep_local_style_blocks(self):
        for relative_path in (
            "templates/portal/dashboard.html",
            "templates/portal/dashboard_role.html",
            "templates/portal/dashboard_show_manager.html",
        ):
            template = (Path(settings.BASE_DIR) / relative_path).read_text()
            self.assertNotIn("<style>", template, relative_path)

    def test_role_dashboard_uses_shared_dashboard_components(self):
        template = (Path(settings.BASE_DIR) / "templates/portal/dashboard_role.html").read_text()

        self.assertIn('class="hero dashboard-hero club-hero"', template)
        self.assertIn('class="dashboard-workspaces"', template)
        self.assertIn("dashboard-role-summary", template)
        self.assertIn("course-status-card", template)
        self.assertIn("quick-actions", template)

    def test_show_manager_is_part_of_dashboard_visual_family(self):
        template = (Path(settings.BASE_DIR) / "templates/portal/dashboard_show_manager.html").read_text()

        self.assertIn('class="hero dashboard-hero show-manager-hero club-hero"', template)
        self.assertIn('class="dashboard-workspaces"', template)
        self.assertIn("show-manager-summary", template)
        self.assertNotIn('class="page-intro"', template)

    def test_dashboard_styles_define_shared_role_and_show_manager_patterns(self):
        css = (Path(settings.BASE_DIR) / "static/css/dashboard-v290.css").read_text()

        for selector in (
            ".dashboard-hero",
            ".quick-actions",
            ".course-status-card",
            ".dashboard-role-summary",
            ".show-manager-summary",
            ".show-manager-hero",
        ):
            self.assertIn(selector, css)
