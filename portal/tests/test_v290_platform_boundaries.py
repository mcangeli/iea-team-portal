from types import SimpleNamespace

from django.core.exceptions import PermissionDenied
from django.test import SimpleTestCase

from portal.modules import DEFAULT_ENABLED_MODULES, enabled_modules_for_organization
from portal.platform import organization_for_user


class ArenaLinePlatformBoundaryTests(SimpleTestCase):
    def test_organization_context_preserves_current_team_tenant(self):
        team = object()
        user = SimpleNamespace(profile=SimpleNamespace(team=team))
        self.assertIs(organization_for_user(user), team)

    def test_optional_organization_context_allows_unassigned_account(self):
        user = SimpleNamespace()
        self.assertIsNone(organization_for_user(user))

    def test_required_organization_context_preserves_permission_behavior(self):
        user = SimpleNamespace(profile=SimpleNamespace(team=None))
        with self.assertRaisesMessage(PermissionDenied, "Your account is not assigned to a team."):
            organization_for_user(user, required=True)

    def test_organization_module_boundary_preserves_preview_3_defaults(self):
        self.assertEqual(enabled_modules_for_organization(object()), DEFAULT_ENABLED_MODULES)
        self.assertEqual(enabled_modules_for_organization(None), DEFAULT_ENABLED_MODULES)
