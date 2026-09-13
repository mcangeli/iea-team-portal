from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class ArenaLineV290ReleaseCandidateTests(SimpleTestCase):
    def setUp(self):
        self.root = Path(settings.BASE_DIR)

    def test_readme_identifies_arenaline_v290(self):
        readme = (self.root / "README.md").read_text(encoding="utf-8")
        self.assertIn("# ArenaLine", readme)
        self.assertIn("**Current version: v2.9.0**", readme)
        self.assertIn("./portalctl update v2.9.0", readme)
        self.assertIn("./portalctl health", readme)
        self.assertIn("docs/BACKUP_RESTORE_ROLLBACK.md", readme)
        self.assertIn("RELEASE_CHECKLIST_v2.9.0.md", readme)
        self.assertNotIn("**Current version: v2.0.0**", readme)
        self.assertNotIn("./portalctl update v2.0.0", readme)

    def test_release_checklist_contains_required_rc_gates(self):
        checklist = (self.root / "RELEASE_CHECKLIST_v2.9.0.md").read_text(encoding="utf-8")
        required = (
            "Application regression gate",
            "Functional visual gate",
            "Security and data-access gate",
            "Staging deployment gate",
            "Production pre-promotion gate",
            "Immediate post-promotion verification",
            "Rollback decision path",
            "Release evidence to retain",
            "./portalctl update v2.9.0",
            "./portalctl health",
            "docs/BACKUP_RESTORE_ROLLBACK.md",
        )
        for marker in required:
            with self.subTest(marker=marker):
                self.assertIn(marker, checklist)

    def test_release_identity_and_checklist_match(self):
        version = (self.root / "VERSION").read_text(encoding="utf-8").strip()
        checklist = (self.root / "RELEASE_CHECKLIST_v2.9.0.md").read_text(encoding="utf-8")
        self.assertEqual(version, "2.9.0")
        self.assertIn(f"ArenaLine v{version}", checklist)
