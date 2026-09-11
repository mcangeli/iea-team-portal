from pathlib import Path

from django.test import SimpleTestCase


class PhotoBrandingTests(SimpleTestCase):
    def test_preview8_branding_fields_and_migration_exist(self):
        root = Path(__file__).resolve().parents[2]
        models = (root / "portal/branding_models.py").read_text()
        self.assertIn("hero_image = models.ImageField", models)
        self.assertIn("hero_image_position = models.CharField", models)
        self.assertTrue((root / "portal/migrations/0031_v200_team_branding.py").exists())

    def test_branding_management_surface_exists(self):
        root = Path(__file__).resolve().parents[2]
        self.assertTrue((root / "portal/branding_urls.py").exists())
        template = (root / "templates/portal/team_branding.html").read_text()
        self.assertIn('enctype="multipart/form-data"', template)
        self.assertIn("LIVE PREVIEW", template)

    def test_dashboard_and_login_support_team_photo(self):
        root = Path(__file__).resolve().parents[2]
        base = (root / "templates/base.html").read_text()
        css = (root / "static/css/photo-v2.css").read_text()
        self.assertIn("portal_team.branding.hero_image.url", base)
        self.assertIn('body[style*="--team-hero-image"] .dashboard-hero', css)
        self.assertIn('body[style*="--team-hero-image"] .login-intro', css)
