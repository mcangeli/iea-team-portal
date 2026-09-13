from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class ArenaLinePeopleContextTests(SimpleTestCase):
    def test_legacy_team_resolver_delegates_to_platform_context(self):
        common = (Path(settings.BASE_DIR) / "portal/view_modules/common.py").read_text()

        self.assertIn("from ..platform import organization_for_view_user", common)
        self.assertIn("return organization_for_view_user(user)", common)
        self.assertNotIn("return user.profile.team if hasattr(user, \"profile\") else None", common)
        self.assertNotIn("if not hasattr(user, \"profile\") or not user.profile.team:", common)

    def test_people_roster_uses_shared_context_resolver_not_profile_storage(self):
        roster = (Path(settings.BASE_DIR) / "portal/view_modules/roster.py").read_text()

        self.assertIn("_team(request.user)", roster)
        self.assertNotIn("request.user.profile.team", roster)
        self.assertNotIn("user.profile.team", roster)

    def test_iea_roster_semantics_remain_intact(self):
        roster = (Path(settings.BASE_DIR) / "portal/view_modules/roster.py").read_text()

        self.assertIn("SeasonMembership.TeamLevel.FUTURES", roster)
        self.assertIn("SeasonMembership.TeamLevel.UPPER", roster)
        self.assertIn('writer.writerow(["Rider", "Email", "Grade", "School", "Team", "Season classes", "IEA member number"])', roster)
