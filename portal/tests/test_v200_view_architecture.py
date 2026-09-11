from django.test import SimpleTestCase

from portal import views


class ViewArchitectureTests(SimpleTestCase):
    """Regression checks for the v2 view-module refactor."""

    def test_public_views_keep_compatibility_namespace(self):
        expected = (
            "dashboard",
            "rider_list",
            "show_detail",
            "my_show_day",
            "standings",
            "lesson_list",
            "season_archive",
            "finance_dashboard",
            "family_account",
            "fundraising_dashboard",
        )
        for name in expected:
            self.assertTrue(hasattr(views, name), name)

    def test_representative_views_are_implemented_in_domain_modules(self):
        expected_modules = {
            "dashboard": "portal.view_modules.roster",
            "show_detail": "portal.view_modules.competitions",
            "my_show_day": "portal.view_modules.show_day",
            "standings": "portal.view_modules.scoring",
            "show_planning": "portal.view_modules.show_planning",
            "lesson_list": "portal.view_modules.lessons",
            "season_archive": "portal.view_modules.history",
            "finance_dashboard": "portal.view_modules.finance_core",
            "family_account": "portal.view_modules.family_finance",
            "fundraising_dashboard": "portal.view_modules.fundraising",
            "finance_reports": "portal.view_modules.finance_reports",
            "show_finance": "portal.view_modules.show_finance",
        }
        for name, module in expected_modules.items():
            self.assertEqual(getattr(views, name).__module__, module)
