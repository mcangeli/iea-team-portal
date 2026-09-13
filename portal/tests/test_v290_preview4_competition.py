from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class ArenaLinePreview4CompetitionTests(SimpleTestCase):
    def test_base_loads_competition_presentation_layer(self):
        base = (Path(settings.BASE_DIR) / "templates/base.html").read_text()
        self.assertIn("css/competition-v290.css", base)

    def test_competition_layer_covers_core_surfaces(self):
        css = (Path(settings.BASE_DIR) / "static/css/competition-v290.css").read_text()

        for selector in (
            ".show-card",
            ".show-hero",
            ".class-card",
            ".honors-board",
            ".season-history-card",
            ".record-award-card",
        ):
            self.assertIn(selector, css)

    def test_iea_competition_semantics_remain_in_templates(self):
        show_detail = (Path(settings.BASE_DIR) / "templates/portal/show_detail.html").read_text()
        standings = (Path(settings.BASE_DIR) / "templates/portal/standings.html").read_text()

        self.assertIn("Point rider", show_detail)
        self.assertIn("advances_to_zones", show_detail)
        self.assertIn("H8/H14 are excluded", show_detail)
        self.assertIn("INDIVIDUAL QUALIFICATION", standings)
        self.assertIn("TEAM QUALIFICATION", standings)
        self.assertIn("individual_qualification_points", standings)
        self.assertIn("team_qualification_points", standings)

    def test_scoring_settings_has_stable_back_navigation(self):
        scoring = (Path(settings.BASE_DIR) / "portal/view_modules/scoring.py").read_text()
        shared_form = (Path(settings.BASE_DIR) / "templates/portal/form.html").read_text()

        self.assertIn('"back_url_name": "season_setup"', scoring)
        self.assertIn('"back_label": "Back to season setup"', scoring)
        self.assertIn("{% if back_url_name %}", shared_form)
        self.assertIn("{% url back_url_name %}", shared_form)
