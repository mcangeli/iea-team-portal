from django.test import SimpleTestCase

from portal.hoofprint_models import HoofprintSnapshot as LegacyHoofprintSnapshot
from portal.horse_models import Horse as LegacyHorse
from portal.model_modules.hoofprint import HoofprintSnapshot
from portal.model_modules.horses import Horse
from portal.model_modules.post_show_horses import ShowHorseHistory
from portal.model_modules.show_readiness import ShowLeasedHorse
from portal.post_show_horse_models import ShowHorseHistory as LegacyShowHorseHistory
from portal.show_readiness_models import ShowLeasedHorse as LegacyShowLeasedHorse


class V290HorseModelModuleTests(SimpleTestCase):
    def test_legacy_imports_resolve_to_canonical_model_classes(self):
        self.assertIs(LegacyHorse, Horse)
        self.assertIs(LegacyHoofprintSnapshot, HoofprintSnapshot)
        self.assertIs(LegacyShowLeasedHorse, ShowLeasedHorse)
        self.assertIs(LegacyShowHorseHistory, ShowHorseHistory)

    def test_relocated_models_remain_in_portal_app(self):
        for model in (Horse, HoofprintSnapshot, ShowLeasedHorse, ShowHorseHistory):
            with self.subTest(model=model.__name__):
                self.assertEqual(model._meta.app_label, "portal")
