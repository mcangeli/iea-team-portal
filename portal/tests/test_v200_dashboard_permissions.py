from pathlib import Path
from django.test import SimpleTestCase


class DashboardPermissionSourceTests(SimpleTestCase):
    def test_workspace_links_distinguish_admin_from_coach(self):
        root = Path(__file__).resolve().parents[2]
        source = (root / "portal/view_modules/dashboards.py").read_text()
        self.assertIn("admin = _is_admin(user)", source)
        self.assertIn('if admin:\n        links.append({"label": "Team overview"', source)
        self.assertIn("admin or profile_role == UserProfile.Role.COACH", source)
        self.assertIn("admin or roles.intersection(parent_roles)", source)
        self.assertIn("admin or CommitteeAssignment.Role.POINTS_SECRETARY in roles", source)
        self.assertIn("admin or has_lead_assignment", source)

    def test_direct_role_dashboards_require_explicit_assignment(self):
        root = Path(__file__).resolve().parents[2]
        source = (root / "portal/view_modules/dashboards.py").read_text()
        self.assertIn("if not _is_admin(request.user):", source)
        self.assertIn("CommitteeAssignment.Role.POINTS_SECRETARY in roles", source)

    def test_coach_dashboard_surfaces_assigned_tasks(self):
        root = Path(__file__).resolve().parents[2]
        context = (root / "portal/context_processors.py").read_text()
        template = (root / "templates/portal/dashboard_role.html").read_text()
        self.assertIn("assigned_to=request.user", context)
        self.assertIn('"portal_assigned_actions": assigned_actions', context)
        self.assertIn("Assigned to you", template)
