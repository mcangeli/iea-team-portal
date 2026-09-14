from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class ArenaLinePeopleContextTests(SimpleTestCase):
    def test_legacy_team_resolver_delegates_to_platform_context(self):
        common = (Path(settings.BASE_DIR) / "portal/view_modules/common.py").read_text()

        self.assertIn("organization_for_view_user", common)
        self.assertIn("return organization_for_view_user(user)", common)
        self.assertNotIn("return user.profile.team if hasattr(user, \"profile\") else None", common)
        self.assertNotIn("if not hasattr(user, \"profile\") or not user.profile.team:", common)

    def test_legacy_active_season_resolver_delegates_to_operating_period_context(self):
        common = (Path(settings.BASE_DIR) / "portal/view_modules/common.py").read_text()

        self.assertIn("active_period_for_organization", common)
        self.assertIn("return active_period_for_organization(team)", common)
        self.assertNotIn("return team.seasons.filter(is_active=True).first()", common)

    def test_people_roster_uses_direct_platform_context_boundary(self):
        roster = (Path(settings.BASE_DIR) / "portal/view_modules/roster.py").read_text()

        self.assertIn("organization_for_view_user", roster)
        self.assertIn("active_period_for_organization", roster)
        self.assertNotIn("_team(request.user)", roster)
        self.assertNotIn("_active_season(", roster)
        self.assertNotIn("request.user.profile.team", roster)

    def test_people_privacy_and_roster_services_remain_intact(self):
        roster = (Path(settings.BASE_DIR) / "portal/view_modules/roster.py").read_text()

        self.assertIn("_can_view_private_rider", roster)
        self.assertIn("_visible_riders", roster)
        self.assertIn("_team_roster", roster)
        self.assertIn("_can_view_family_account", roster)

    def test_iea_roster_semantics_remain_intact(self):
        roster = (Path(settings.BASE_DIR) / "portal/view_modules/roster.py").read_text()

        self.assertIn("SeasonMembership.TeamLevel.FUTURES", roster)
        self.assertIn("SeasonMembership.TeamLevel.UPPER", roster)
        self.assertIn('writer.writerow(["Rider", "Email", "Grade", "School", "Team", "Season classes", "IEA member number"])', roster)
        self.assertIn("rider.iea_member_number", roster)
        self.assertIn("team_level=form.cleaned_data", roster)
        self.assertIn("team and class assignments updated", roster)

    def test_persisted_team_and_season_fields_stay_behind_boundary(self):
        roster = (Path(settings.BASE_DIR) / "portal/view_modules/roster.py").read_text()

        self.assertIn("obj.team = team", roster)
        self.assertIn("guardian.team = team", roster)
        self.assertIn("season__team=team", roster)
        self.assertIn("GuardianContact.objects.filter(team=team)", roster)
