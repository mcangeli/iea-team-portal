from pathlib import Path

from django.conf import settings
from django.test import TestCase
from django.urls import reverse


class ArenaLineOrganizationShellTests(TestCase):
    def test_login_context_exposes_generic_organization_contract_and_compat_alias(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("portal_organization", response.context)
        self.assertIn("portal_team", response.context)
        self.assertIs(response.context["portal_organization"], response.context["portal_team"])

    def test_base_shell_uses_generic_organization_context(self):
        base = (Path(settings.BASE_DIR) / "templates/base.html").read_text()

        self.assertIn("portal_organization", base)
        self.assertNotIn("portal_team", base)
        self.assertIn("portal_organization.logo", base)
        self.assertIn("portal_organization.name", base)
        self.assertIn("portal_organization.branding.hero_image", base)

    def test_branding_entry_point_uses_platform_organization_boundary(self):
        branding_views = (Path(settings.BASE_DIR) / "portal/view_modules/branding.py").read_text()

        self.assertIn("organization_for_user(request.user, required=True)", branding_views)
        self.assertIn("TeamBranding.objects.get_or_create(team=organization)", branding_views)
        self.assertIn('"organization": organization', branding_views)
        self.assertNotIn("_team(request.user)", branding_views)
