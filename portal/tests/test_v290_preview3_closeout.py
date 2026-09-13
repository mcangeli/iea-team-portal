from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

from portal.modules import ARENA_MODULES, DEFAULT_ENABLED_MODULES


class ArenaLinePreview3CloseoutTests(SimpleTestCase):
    def _read(self, relative_path):
        return (Path(settings.BASE_DIR) / relative_path).read_text()

    def test_stable_module_contract_is_complete(self):
        self.assertEqual(
            tuple(ARENA_MODULES.keys()),
            (
                "core",
                "people",
                "horses",
                "competition_iea",
                "operations",
                "finance",
                "communications",
            ),
        )
        self.assertEqual(DEFAULT_ENABLED_MODULES, tuple(ARENA_MODULES.keys()))
        self.assertEqual(ARENA_MODULES["competition_iea"]["scope"], "competition")
        for module_id in ("core", "people", "horses", "operations", "finance", "communications"):
            self.assertEqual(ARENA_MODULES[module_id]["scope"], "platform")

    def test_shared_shell_uses_generic_organization_contract(self):
        base = self._read("templates/base.html")
        context = self._read("portal/context_processors.py")

        self.assertIn("portal_organization", base)
        self.assertNotIn("portal_team", base)
        self.assertIn('"portal_organization": organization', context)
        self.assertIn('"portal_team": organization', context)

    def test_legacy_context_helpers_delegate_to_platform_services(self):
        common = self._read("portal/view_modules/common.py")

        self.assertIn("return organization_for_view_user(user)", common)
        self.assertIn("return active_period_for_organization(team)", common)
        self.assertNotIn('raise PermissionDenied("Your account is not assigned to a team.")', common)

    def test_generic_domains_do_not_read_profile_team_directly(self):
        generic_domain_files = (
            "portal/view_modules/administration.py",
            "portal/view_modules/branding.py",
            "portal/view_modules/communications.py",
            "portal/view_modules/family_finance.py",
            "portal/view_modules/horses.py",
            "portal/view_modules/lessons.py",
            "portal/view_modules/roster.py",
        )
        for relative_path in generic_domain_files:
            source = self._read(relative_path)
            self.assertNotIn("request.user.profile.team", source, relative_path)

    def test_iea_competition_semantics_remain_specialized(self):
        competition = self._read("portal/view_modules/competitions.py")
        roster = self._read("portal/view_modules/roster.py")

        self.assertIn("_team(request.user)", competition)
        self.assertIn("SeasonMembership.TeamLevel.FUTURES", roster)
        self.assertIn("SeasonMembership.TeamLevel.UPPER", roster)
        self.assertIn("IEA member number", roster)
