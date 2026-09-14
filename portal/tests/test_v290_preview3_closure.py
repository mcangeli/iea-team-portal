from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class ArenaLinePreview3ClosureTests(SimpleTestCase):
    def _source(self, name):
        return (Path(settings.BASE_DIR) / "portal/view_modules" / name).read_text()

    def test_horses_use_platform_organization_context(self):
        source = self._source("horses.py")

        self.assertIn("organization_for_view_user", source)
        self.assertIn("active_period_for_organization", source)
        self.assertNotIn("_team(request.user)", source)
        self.assertNotIn("team = _team(user)", source)

    def test_lessons_and_volunteers_use_platform_context(self):
        source = self._source("lessons.py")

        self.assertIn("organization_for_view_user", source)
        self.assertIn("active_period_for_organization", source)
        self.assertNotIn("_team(request.user)", source)
        self.assertNotIn("_active_season(", source)
        self.assertIn('writer.writerow(["Team", "Rider", "Required", "Approved", "Pending", "Remaining", "Complete"])', source)

    def test_role_dashboards_use_platform_context(self):
        source = self._source("dashboards.py")

        self.assertIn("organization_for_view_user", source)
        self.assertIn("active_period_for_organization", source)
        self.assertNotIn("_team(request.user)", source)
        self.assertNotIn("_active_season(", source)
        self.assertIn("SeasonMembership.TeamLevel.FUTURES", source)
        self.assertIn("SeasonMembership.TeamLevel.UPPER", source)

    def test_legacy_finance_callers_remain_behind_platform_compatibility_seam(self):
        common = self._source("common.py")

        self.assertIn("def _team(user):", common)
        self.assertIn("return organization_for_view_user(user)", common)
        self.assertIn("def _active_season(team):", common)
        self.assertIn("return active_period_for_organization(team)", common)
