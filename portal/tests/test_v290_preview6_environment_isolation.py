from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


def _env_values(path):
    values = {}
    for raw_line in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


class ArenaLineDeploymentIsolationTests(SimpleTestCase):
    def setUp(self):
        root = Path(settings.BASE_DIR)
        self.production = _env_values(root / ".env.example")
        self.staging = _env_values(root / ".env.staging.example")
        self.compose = (root / "docker-compose.yml").read_text(encoding="utf-8")
        self.staging_doc = (root / "docs/STAGING.md").read_text(encoding="utf-8")

    def test_staging_and_production_use_distinct_compose_identity(self):
        for key in (
            "COMPOSE_PROJECT_NAME",
            "POSTGRES_VOLUME_NAME",
            "MEDIA_VOLUME_NAME",
            "APP_PORT",
            "POSTGRES_DB",
            "POSTGRES_USER",
        ):
            self.assertTrue(self.production.get(key), key)
            self.assertTrue(self.staging.get(key), key)
            self.assertNotEqual(self.production[key], self.staging[key], key)

    def test_environment_roles_and_update_channels_are_explicit(self):
        self.assertEqual(self.production["PORTAL_ENVIRONMENT"], "production")
        self.assertEqual(self.staging["PORTAL_ENVIRONMENT"], "staging")
        self.assertEqual(self.production["PORTAL_UPDATE_CHANNEL"], "stable")
        self.assertEqual(self.staging["PORTAL_UPDATE_CHANNEL"], "preview")

    def test_staging_email_is_disabled_by_default(self):
        self.assertEqual(self.staging["EMAIL_HOST"], "")
        self.assertEqual(self.staging["DEFAULT_FROM_EMAIL"], "staging@example.invalid")

    def test_staging_security_defaults_match_private_local_access(self):
        self.assertEqual(self.staging["SECURE_COOKIES"], "0")
        self.assertEqual(self.staging["SECURE_HSTS_SECONDS"], "0")
        self.assertEqual(self.production["SECURE_COOKIES"], "1")
        self.assertNotEqual(self.production["SECURE_HSTS_SECONDS"], "0")

    def test_compose_volumes_are_environment_selected(self):
        self.assertIn("${POSTGRES_VOLUME_NAME:-iea-team-portal_postgres_data}", self.compose)
        self.assertIn("${MEDIA_VOLUME_NAME:-iea-team-portal_media_data}", self.compose)
        self.assertIn("${COMPOSE_PROJECT_NAME:-iea-team-portal}", self.compose)
        self.assertIn("127.0.0.1:${APP_PORT:-8088}:8080", self.compose)

    def test_staging_guide_requires_explicit_volume_verification(self):
        self.assertIn("Do not continue if those commands resolve to the production volume names.", self.staging_doc)
        self.assertIn("Never remove `iea-team-portal_postgres_data`", self.staging_doc)
        self.assertIn("confirm `EMAIL_HOST` is still blank", self.staging_doc)
