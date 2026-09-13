from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class ArenaLineFinanceContextTests(SimpleTestCase):
    def test_family_finance_uses_organization_context(self):
        source = (Path(settings.BASE_DIR) / "portal/view_modules/family_finance.py").read_text()

        self.assertIn("organization_for_user", source)
        self.assertIn("active_period_for_organization", source)
        self.assertNotIn("_team(request.user)", source)
        self.assertNotIn("_active_season(", source)

    def test_finance_keeps_persisted_team_and_season_fields_behind_boundary(self):
        source = (Path(settings.BASE_DIR) / "portal/view_modules/family_finance.py").read_text()

        self.assertIn("team=team", source)
        self.assertIn("season__team=team", source)
        self.assertIn("obj.team = team", source)
        self.assertIn("obj.season = season", source)

    def test_finance_permission_and_audit_services_remain_in_place(self):
        source = (Path(settings.BASE_DIR) / "portal/view_modules/family_finance.py").read_text()

        self.assertIn("_require_finance(request.user", source)
        self.assertIn("_audit_event(", source)
        self.assertIn("_can_view_family_account", source)
