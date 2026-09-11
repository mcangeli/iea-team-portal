from pathlib import Path

from django.test import SimpleTestCase

from portal.lifecycle_models import RiderLifecycle


class RiderLifecycleArchitectureTests(SimpleTestCase):
    def test_explicit_statuses(self):
        self.assertEqual(
            {value for value, _label in RiderLifecycle.Status.choices},
            {"active", "graduated", "left_team", "inactive"},
        )

    def test_archive_templates_exist(self):
        project_root = Path(__file__).resolve().parents[2]
        self.assertTrue((project_root / "templates/portal/former_rider_list.html").exists())
        self.assertTrue((project_root / "templates/portal/rider_lifecycle_form.html").exists())

    def test_lifecycle_migration_exists(self):
        project_root = Path(__file__).resolve().parents[2]
        self.assertTrue((project_root / "portal/migrations/0030_v200_rider_lifecycle.py").exists())
