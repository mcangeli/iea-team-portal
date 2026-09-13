from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class Preview6ReleaseIdentityTests(SimpleTestCase):
    def test_version_file_and_django_settings_agree(self):
        version_file = (Path(settings.BASE_DIR) / "VERSION").read_text(encoding="utf-8").strip()
        self.assertEqual(version_file, "2.9.0")
        self.assertEqual(settings.SITE_VERSION, version_file)

    def test_portalctl_uses_version_file_for_upgrade_identity(self):
        portalctl = (Path(settings.BASE_DIR) / "portalctl").read_text(encoding="utf-8")
        self.assertIn('RELEASE_VERSION="$(cat "$SCRIPT_DIR/VERSION"', portalctl)
        self.assertIn('backup="$ROOT_DIR/backups/pre-v${RELEASE_VERSION}-$stamp.sql"', portalctl)
        self.assertIn('UPGRADE_LOG="$ROOT_DIR/logs/upgrade-v${RELEASE_VERSION}-$stamp.log"', portalctl)
        self.assertIn('echo "Starting v${RELEASE_VERSION}..."', portalctl)

    def test_ui_version_links_to_matching_release_tag(self):
        context_processor = (Path(settings.BASE_DIR) / "portal/context_processors.py").read_text(encoding="utf-8")
        self.assertIn('"site_version": settings.SITE_VERSION', context_processor)
        self.assertIn('f"{settings.PORTAL_REPOSITORY_URL}/tree/v{settings.SITE_VERSION}"', context_processor)
