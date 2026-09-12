from django.apps import apps
from django.test import SimpleTestCase

from portal.branding_models import TeamBranding as LegacyTeamBranding
from portal.model_modules.branding import TeamBranding


class V290ModelModuleArchitectureTests(SimpleTestCase):
    def test_branding_model_uses_model_modules_package(self):
        self.assertEqual(TeamBranding.__module__, "portal.model_modules.branding")
        self.assertEqual(TeamBranding._meta.app_label, "portal")
        self.assertIs(apps.get_model("portal", "TeamBranding"), TeamBranding)

    def test_legacy_branding_import_remains_compatible(self):
        self.assertIs(LegacyTeamBranding, TeamBranding)
