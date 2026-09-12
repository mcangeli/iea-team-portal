from pathlib import Path

from django.db import models
from django.test import SimpleTestCase

from portal.branding_models import TeamBranding


class SquadBrandingSourceTests(SimpleTestCase):
    def test_squad_branding_fields_and_migration_exist(self):
        root = Path(__file__).resolve().parents[2]
        self.assertIsInstance(TeamBranding._meta.get_field("futures_hero_image"), models.ImageField)
        self.assertIsInstance(TeamBranding._meta.get_field("upper_hero_image"), models.ImageField)
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
