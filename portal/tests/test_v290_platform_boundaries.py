from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.core.exceptions import PermissionDenied
from django.test import SimpleTestCase

from portal.models import UserProfile
from portal.modules import DEFAULT_ENABLED_MODULES, enabled_modules_for_organization
from portal.platform import (
    active_period_for_organization,
    can_manage_organization,
    default_organization,
    organization_for_user,
    role_for_user,
)


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

    def test_default_organization_hides_persisted_team_lookup_from_shell_code(self):
        expected = object()
        ordered = Mock()
        ordered.first.return_value = expected
        with patch("portal.platform.Team.objects.order_by", return_value=ordered) as order_by:
            self.assertIs(default_organization(), expected)
        order_by.assert_called_once_with("pk")

    def test_active_period_hides_season_storage_from_generic_platform_code(self):
        organization = object()
        expected = object()
        filtered = Mock()
        filtered.first.return_value = expected
        with patch("portal.platform.Season.objects.filter", return_value=filtered) as filter_periods:
            self.assertIs(active_period_for_organization(organization), expected)
        filter_periods.assert_called_once_with(team=organization, is_active=True)

    def test_active_period_is_none_without_organization(self):
        self.assertIsNone(active_period_for_organization(None))

    def test_role_boundary_preserves_profile_roles(self):
        user = SimpleNamespace(profile=SimpleNamespace(role=UserProfile.Role.COACH))
        self.assertEqual(role_for_user(user), UserProfile.Role.COACH)
        self.assertIsNone(role_for_user(SimpleNamespace()))

    def test_organization_management_boundary_preserves_current_authority(self):
        admin = SimpleNamespace(
            is_superuser=False,
            profile=SimpleNamespace(role=UserProfile.Role.ADMIN),
        )
        coach = SimpleNamespace(
            is_superuser=False,
            profile=SimpleNamespace(role=UserProfile.Role.COACH),
        )
        parent = SimpleNamespace(
            is_superuser=False,
            profile=SimpleNamespace(role=UserProfile.Role.PARENT),
        )
        superuser = SimpleNamespace(is_superuser=True)

        self.assertTrue(can_manage_organization(admin))
        self.assertTrue(can_manage_organization(coach))
        self.assertTrue(can_manage_organization(superuser))
        self.assertFalse(can_manage_organization(parent))

    def test_organization_module_boundary_preserves_preview_3_defaults(self):
        self.assertEqual(enabled_modules_for_organization(object()), DEFAULT_ENABLED_MODULES)
        self.assertEqual(enabled_modules_for_organization(None), DEFAULT_ENABLED_MODULES)
