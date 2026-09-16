from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class SensitiveMediaGatewayTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.caddyfile = (Path(settings.BASE_DIR) / "Caddyfile").read_text(encoding="utf-8")

    def test_generic_horse_documents_are_not_public_media(self):
        self.assertIn("handle /media/horses/documents/*", self.caddyfile)
        self.assertIn('respond "Not Found" 404', self.caddyfile)

    def test_coggins_documents_are_not_public_media(self):
        self.assertIn("handle /media/horses/coggins/*", self.caddyfile)

    def test_show_horse_lists_are_not_public_media(self):
        self.assertIn("handle /media/show_horse_lists/*", self.caddyfile)
