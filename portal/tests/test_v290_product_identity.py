from pathlib import Path

from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from portal.context_processors import PRODUCT_NAME, PRODUCT_TAGLINE


class ArenaLineProductIdentityTests(TestCase):
    def test_product_identity_constants(self):
        self.assertEqual(PRODUCT_NAME, "ArenaLine")
        self.assertEqual(PRODUCT_TAGLINE, "One team. One season. One place to manage it.")

    def test_login_page_uses_arenaline_identity(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign in · ArenaLine")
        self.assertContains(response, "WELCOME TO ARENALINE")
        self.assertContains(response, "Enter ArenaLine")
        self.assertContains(response, "One team. One season. One place to manage it.")
        self.assertContains(response, "/static/brand/arenaline-favicon.")
        self.assertContains(response, "/static/brand/arenaline-geometric-mark.")
        self.assertContains(response, "/static/css/arenaline-v290.")
        self.assertNotContains(response, "Team Portal")

    def test_brand_styles_keep_light_and_dark_modes(self):
        css = (Path(settings.BASE_DIR) / "static/css/arenaline-v290.css").read_text()
        self.assertIn('html[data-theme="light"]', css)
        self.assertIn('html[data-theme="dark"]', css)
        self.assertIn("--arena-navy:#0E2A47", css)
        self.assertIn("--arena-gold:#C9A96B", css)
        self.assertIn("--arena-blue:#007297", css)

    def test_primary_surfaces_use_arenaline_language(self):
        templates = Path(settings.BASE_DIR) / "templates/portal"
        dashboard = (templates / "dashboard.html").read_text()
        my_team = (templates / "my_team.html").read_text()
        show_manager = (templates / "dashboard_show_manager.html").read_text()

        self.assertIn("Dashboard · ArenaLine", dashboard)
        self.assertIn("ARENALINE · SEASON HOME", dashboard)
        self.assertNotIn("Equestrian Team Portal", dashboard)
        self.assertIn("My Team · ArenaLine", my_team)
        self.assertIn("ARENALINE · TEAM HUB", my_team)
        self.assertIn("Show Manager · ArenaLine", show_manager)
        self.assertIn("ARENALINE · SHOW HOST OPERATIONS", show_manager)
