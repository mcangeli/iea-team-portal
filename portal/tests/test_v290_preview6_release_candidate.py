from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class ArenaLineReleaseDocumentationTests(SimpleTestCase):
    def setUp(self):
        self.root = Path(settings.BASE_DIR)
        self.version = (self.root / "VERSION").read_text(encoding="utf-8").strip()

    def test_readme_identifies_current_arenaline_release(self):
        readme = (self.root / "README.md").read_text(encoding="utf-8")
        self.assertIn("# ArenaLine", readme)
        self.assertIn(f"**Current version: v{self.version}**", readme)
        self.assertIn(f"./portalctl update v{self.version}", readme)
        self.assertIn("./portalctl update", readme)
        self.assertIn("./portalctl health", readme)
        self.assertIn("docs/BACKUP_RESTORE_ROLLBACK.md", readme)
        self.assertIn("RELEASE_CHECKLIST.md", readme)

    def test_canonical_release_checklist_contains_required_promotion_gates(self):
        checklist = (self.root / "RELEASE_CHECKLIST.md").read_text(encoding="utf-8")
        required = (
            "VERSION",
            "README.md",
            "RELEASE_NOTES.md",
            "ROADMAP.md",
            "ARCHITECTURE.md",
            "main",
            "tag",
            "portalctl",
        )
        for marker in required:
            with self.subTest(marker=marker):
                self.assertIn(marker, checklist)

    def test_release_identity_and_settings_match(self):
        self.assertEqual(settings.SITE_VERSION, self.version)
