from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class ArenaLineAdministrationContextTests(SimpleTestCase):
    def test_administration_uses_platform_organization_context(self):
        source = (Path(settings.BASE_DIR) / "portal/view_modules/administration.py").read_text()

        self.assertIn("organization_for_view_user", source)
        self.assertIn("active_period_for_organization", source)
        self.assertNotIn("_team(request.user)", source)
        self.assertNotIn("_active_season(", source)

    def test_administration_keeps_persisted_team_fields_behind_boundary(self):
        source = (Path(settings.BASE_DIR) / "portal/view_modules/administration.py").read_text()

        self.assertIn("profile__team=team", source)
        self.assertIn("CommitteeAssignment.objects.filter(team=team", source)
        self.assertIn("Season.objects.filter(team=team)", source)

    def test_audit_log_uses_generic_organization_presentation(self):
        source = (Path(settings.BASE_DIR) / "portal/view_modules/administration.py").read_text()

        self.assertIn('"audit_title": "Organization audit log"', source)
        self.assertIn("important organization, competition, user, and finance changes", source)
        self.assertNotIn('"audit_title": "Team audit log"', source)
