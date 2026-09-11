from pathlib import Path

from django.test import SimpleTestCase


class ThemeStabilizationTests(SimpleTestCase):
    def test_preview6_theme_tokens_exist(self):
        root = Path(__file__).resolve().parents[2]
        css = (root / "static/css/theme-v2.css").read_text()
        self.assertIn("v2.0 Preview 6 — unified light/dark design system", css)
        self.assertIn('html[data-theme="light"]', css)
        self.assertIn('html[data-theme="dark"]', css)
        self.assertIn("--surface-raised:", css)
        self.assertIn("--control-bg:", css)

    def test_base_honors_system_theme_preference(self):
        root = Path(__file__).resolve().parents[2]
        template = (root / "templates/base.html").read_text()
        self.assertIn("prefers-color-scheme: dark", template)
        self.assertIn("localStorage.getItem('iea-theme')", template)

    def test_no_preview6_migration(self):
        root = Path(__file__).resolve().parents[2]
        self.assertFalse(list((root / "portal/migrations").glob("0031_v200*.py")))
