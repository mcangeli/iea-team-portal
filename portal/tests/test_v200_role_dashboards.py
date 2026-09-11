from pathlib import Path

from django.test import SimpleTestCase
from django.urls import reverse

from portal import views


class RoleDashboardArchitectureTests(SimpleTestCase):
    def test_dashboard_views_live_in_dashboard_module(self):
        for name in (
            "dashboard",
            "dashboard_general",
            "dashboard_coach",
            "dashboard_team_parent",
            "dashboard_show_lead",
            "dashboard_secretary",
        ):
            view = getattr(views, name)
            self.assertEqual(view.__module__, "portal.view_modules.dashboards")

    def test_dashboard_routes_resolve(self):
        expected = {
            "dashboard": "/",
            "dashboard_general": "/dashboard/team/",
            "dashboard_coach": "/dashboard/coach/",
            "dashboard_team_parent": "/dashboard/team-parent/",
            "dashboard_show_lead": "/dashboard/show-lead/",
            "dashboard_secretary": "/dashboard/points/",
        }
        for name, path in expected.items():
            self.assertEqual(reverse(name), path)

    def test_role_dashboard_template_exists(self):
        project_root = Path(__file__).resolve().parents[2]
        self.assertTrue((project_root / "templates/portal/dashboard_role.html").exists())
