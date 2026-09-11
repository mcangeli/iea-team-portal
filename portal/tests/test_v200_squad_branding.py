from pathlib import Path
from django.test import SimpleTestCase

class SquadBrandingSourceTests(SimpleTestCase):
    def test_squad_branding_fields_and_migration_exist(self):
        root = Path(__file__).resolve().parents[2]
        model = (root / "portal/branding_models.py").read_text()
        self.assertIn("futures_hero_image", model)
        self.assertIn("upper_hero_image", model)
        self.assertTrue((root / "portal/migrations/0032_v200_squad_hero_images.py").exists())

    def test_branding_screen_supports_three_hero_levels(self):
        root = Path(__file__).resolve().parents[2]
        template = (root / "templates/portal/team_branding.html").read_text()
        self.assertIn("FUTURES TEAM", template)
        self.assertIn("UPPER TEAM", template)

    def test_squad_heroes_are_permission_contextual(self):
        root = Path(__file__).resolve().parents[2]
        tags = (root / "portal/templatetags/portal_access.py").read_text()
        self.assertIn("def family_squad_hero", tags)
        self.assertIn("len(levels) == 1", tags)
