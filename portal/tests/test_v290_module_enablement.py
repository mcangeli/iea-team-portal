from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

from portal.modules import (
    ARENA_MODULES,
    DEFAULT_ENABLED_MODULES,
    module_is_enabled,
    resolve_enabled_modules,
)


class ArenaLineModuleEnablementTests(SimpleTestCase):
    def test_default_resolution_preserves_all_existing_modules(self):
        self.assertEqual(resolve_enabled_modules(), DEFAULT_ENABLED_MODULES)
        self.assertEqual(DEFAULT_ENABLED_MODULES, tuple(ARENA_MODULES.keys()))

    def test_explicit_resolution_is_registry_ordered_and_core_is_required(self):
        self.assertEqual(
            resolve_enabled_modules(["communications", "people"]),
            ("core", "people", "communications"),
        )

    def test_unknown_module_ids_are_rejected_at_the_platform_boundary(self):
        enabled = resolve_enabled_modules(["people", "not-a-module"])
        self.assertEqual(enabled, ("core", "people"))
        self.assertFalse(module_is_enabled("not-a-module", enabled))

    def test_module_helper_uses_same_resolution_contract(self):
        enabled = ("people",)
        self.assertTrue(module_is_enabled("core", enabled))
        self.assertTrue(module_is_enabled("people", enabled))
        self.assertFalse(module_is_enabled("horses", enabled))

    def test_shell_navigation_is_gated_by_stable_module_ids(self):
        base = (Path(settings.BASE_DIR) / "templates/base.html").read_text()

        for module_id in (
            "core",
            "people",
            "horses",
            "competition_iea",
            "operations",
            "finance",
            "communications",
        ):
            self.assertIn(f'"{module_id}" in portal_enabled_modules', base)

        self.assertIn('data-module="people"', base)
        self.assertIn('data-module="horses"', base)
        self.assertIn('data-module="competition_iea"', base)
        self.assertIn('data-module="operations"', base)
        self.assertIn('data-module="finance"', base)
        self.assertIn('data-module="communications"', base)
