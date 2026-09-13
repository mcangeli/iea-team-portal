from django.test import SimpleTestCase

from portal.apps import PortalConfig


class V290AppLoadingTests(SimpleTestCase):
    def test_season_class_code_behavior_is_not_loaded_as_model_module(self):
        """Behavior-only modules should be loaded from AppConfig.ready(), not import_models()."""
        import inspect

        source = inspect.getsource(PortalConfig.import_models)
        self.assertNotIn("season_class_code", source)

    def test_season_class_code_receivers_are_registered(self):
        """The class-code synchronization behavior must still load during app startup."""
        from portal import season_class_code

        self.assertTrue(callable(season_class_code.inherit_season_class_code))
        self.assertTrue(callable(season_class_code.sync_show_class_codes))
