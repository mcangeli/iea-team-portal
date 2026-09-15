from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class ArenaLinePreview4AdministrationTests(SimpleTestCase):
    def test_base_loads_administration_presentation_layer(self):
        base = (Path(settings.BASE_DIR) / "templates/base.html").read_text()
        self.assertIn("css/admin-v290.css", base)

    def test_history_back_links_have_shared_handler(self):
        base = (Path(settings.BASE_DIR) / "templates/base.html").read_text()
        form_template = (Path(settings.BASE_DIR) / "templates/portal/form.html").read_text()
        delete_template = (Path(settings.BASE_DIR) / "templates/portal/confirm_delete.html").read_text()

        self.assertIn("data-history-back", base)
        self.assertIn("window.history.back()", base)
        self.assertIn("window.location.href='/'", base)
        self.assertIn("data-history-back", form_template)
        self.assertIn("data-history-back", delete_template)
        self.assertNotIn("javascript:history.back()", delete_template)

    def test_administration_layer_covers_core_surfaces(self):
        css = (Path(settings.BASE_DIR) / "static/css/admin-v290.css").read_text()

        for selector in (
            ".section-user_list .table-card",
            ".section-season_setup .team-panel",
            ".section-team_branding .branding-layout",
            ".form-card",
            ".danger-card",
            ".danger-btn",
        ):
            self.assertIn(selector, css)

    def test_season_setup_preserves_iea_team_and_class_semantics(self):
        template = (Path(settings.BASE_DIR) / "templates/portal/season_setup.html").read_text()

        self.assertIn("Futures Team", template)
        self.assertIn("Upper School Team", template)
        self.assertIn("season_class_create", template)
        self.assertIn("class_code", template)
        self.assertIn("HORSE &amp; HOOFPRINT MANAGEMENT", template)

    def test_user_administration_status_semantics_remain(self):
        template = (Path(settings.BASE_DIR) / "templates/portal/user_list.html").read_text()

        self.assertIn("must_change_password", template)
        self.assertIn("user_reset_password", template)
        self.assertIn("account.arena_person", template)
        self.assertIn("Legacy account · no Person linked", template)
        self.assertIn("Manage access", template)
