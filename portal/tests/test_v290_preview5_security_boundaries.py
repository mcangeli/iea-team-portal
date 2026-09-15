from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.test import SimpleTestCase

from portal.models import UserProfile
from portal.platform import organization_for_view_user
from portal.view_modules.common import _can_finance


class ArenaLinePreview5SecurityBoundaryTests(SimpleTestCase):
    def test_normal_account_cannot_resolve_an_unassigned_organization(self):
        user = SimpleNamespace(is_superuser=False, profile=SimpleNamespace(team=None))
        with self.assertRaises(PermissionDenied):
            organization_for_view_user(user)

    def test_rider_finance_denial_precedes_delegated_committee_roles(self):
        rider = SimpleNamespace(
            is_authenticated=True,
            is_superuser=False,
            profile=SimpleNamespace(role=UserProfile.Role.RIDER),
        )
        with patch("portal.view_modules.common._active_committee_roles") as committee_roles:
            self.assertFalse(_can_finance(rider))
        committee_roles.assert_not_called()

    def test_finance_dashboard_requires_finance_and_organization_scoping(self):
        source = (Path(settings.BASE_DIR) / "portal/view_modules/finance_core.py").read_text()
        self.assertIn("_require_finance(request.user, season)", source)
        self.assertIn("FinancialTransaction.objects.filter(team=team", source)
        self.assertIn("AuditEvent.objects.filter(team=team, season_id__in=season_ids)", source)

    def test_people_domain_uses_shared_visibility_boundaries(self):
        source = (Path(settings.BASE_DIR) / "portal/view_modules/roster.py").read_text()
        self.assertIn("_visible_riders(request.user, team)", source)
        self.assertIn("_can_view_family_account(request.user, membership)", source)

    def test_shared_privacy_helpers_delegate_to_people_and_keep_family_visibility_narrow(self):
        source = (Path(settings.BASE_DIR) / "portal/view_modules/common.py").read_text()
        self.assertIn("personal_riders_for_user", source)
        self.assertIn("visible_riders_for_user", source)
        self.assertIn("can_view_private_rider", source)
        self.assertIn("can_view_family_account", source)
        self.assertIn("if not item.family_visible", source)
        self.assertIn("return False", source)
