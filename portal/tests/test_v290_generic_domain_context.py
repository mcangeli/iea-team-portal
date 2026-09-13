from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class ArenaLineGenericDomainContextTests(SimpleTestCase):
    def test_operations_and_communications_use_organization_context(self):
        source = (Path(settings.BASE_DIR) / "portal/view_modules/communications.py").read_text()

        self.assertIn("organization_for_user", source)
        self.assertIn("active_period_for_organization", source)
        self.assertNotIn("_team(request.user)", source)
        self.assertNotIn("_active_season(", source)

    def test_persisted_team_fields_remain_compatibility_details(self):
        source = (Path(settings.BASE_DIR) / "portal/view_modules/communications.py").read_text()

        self.assertIn("team=organization", source)
        self.assertIn("obj.team = organization", source)
        self.assertIn("season=period", source)
        self.assertIn("obj.season = period", source)

    def test_generic_calendar_delete_copy_uses_organization_language(self):
        source = (Path(settings.BASE_DIR) / "portal/view_modules/communications.py").read_text()

        self.assertIn("other organization record", source)
        self.assertNotIn("other team record", source)

    def test_footer_mark_uses_high_contrast_theme_treatment(self):
        css = (Path(settings.BASE_DIR) / "static/css/arenaline-v290.css").read_text()

        self.assertIn(
            'html[data-theme="light"] footer .arena-footer-signature:before{background:color-mix(in srgb,var(--arena-navy) 88%,black)}',
            css,
        )
        self.assertIn(
            'html[data-theme="dark"] footer .arena-footer-signature:before{background:color-mix(in srgb,var(--arena-gold) 82%,white)}',
            css,
        )
