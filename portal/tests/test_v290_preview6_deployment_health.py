from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class Preview6DeploymentHealthContractTests(SimpleTestCase):
    def setUp(self):
        self.root = Path(settings.BASE_DIR)
        self.portalctl = (self.root / "portalctl").read_text(encoding="utf-8")
        self.compose = (self.root / "docker-compose.yml").read_text(encoding="utf-8")
        self.dockerfile = (self.root / "Dockerfile").read_text(encoding="utf-8")
        self.caddy = (self.root / "Caddyfile").read_text(encoding="utf-8")

    def test_portalctl_verifies_database_backup_integrity(self):
        self.assertIn("verify_database_backup()", self.portalctl)
        self.assertIn("^-- PostgreSQL database dump", self.portalctl)
        self.assertIn('verify_database_backup "$backup"', self.portalctl)
        self.assertIn('verify_database_backup "$GIT_UPDATE_BACKUP"', self.portalctl)

    def test_portalctl_has_reusable_deployment_health_command(self):
        self.assertIn("deployment_health()", self.portalctl)
        self.assertIn('health)', self.portalctl)
        self.assertIn("Deployment health check passed for ArenaLine", self.portalctl)

    def test_health_checks_cover_database_django_static_media_and_gateway(self):
        for marker in (
            "pg_isready",
            "python manage.py check",
            "python manage.py portal_preflight",
            "/app/staticfiles/staticfiles.json",
            "/app/media",
            "caddy validate --config /etc/caddy/Caddyfile",
        ):
            self.assertIn(marker, self.portalctl)

    def test_upgrade_update_and_rollback_run_post_start_health(self):
        self.assertGreaterEqual(self.portalctl.count("deployment_health"), 5)
        self.assertIn("compose up -d --build\n    deployment_health", self.portalctl)

    def test_compose_and_image_keep_core_runtime_guards(self):
        self.assertIn("condition: service_healthy", self.compose)
        self.assertIn("pg_isready", self.compose)
        self.assertIn("media_data:/app/media", self.compose)
        self.assertIn("collectstatic --noinput", self.dockerfile)
        self.assertIn("python manage.py portal_preflight", self.dockerfile)

    def test_finance_media_is_not_publicly_served(self):
        self.assertIn("handle /media/finance/*", self.caddy)
        self.assertIn('respond "Not Found" 404', self.caddy)
