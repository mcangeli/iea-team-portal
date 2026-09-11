from types import SimpleNamespace

from django.test import SimpleTestCase

from portal.hoofprint_checks import hoofprint_warnings, live_differs_from_snapshot


class HoofprintCheckTests(SimpleTestCase):
    def test_live_payload_matches_latest_snapshot(self):
        payload = {"show": {"id": 1}, "horses": [{"horse_id": 2}], "coach_name": "Current Coach"}
        snapshot = SimpleNamespace(payload={"show": {"id": 1}, "horses": [{"horse_id": 2}], "coach_name": "Earlier Coach"})
        self.assertFalse(live_differs_from_snapshot(payload, snapshot))

    def test_horse_plan_change_marks_live_payload_different(self):
        snapshot = SimpleNamespace(payload={"show": {"id": 1}, "horses": [{"horse_id": 2}]})
        live = {"show": {"id": 1}, "horses": [{"horse_id": 2}, {"horse_id": 3}]}
        self.assertTrue(live_differs_from_snapshot(live, snapshot))

    def test_completeness_warnings_are_advisory_and_specific(self):
        payload = {"horses": [{
            "barn_name": "Scout",
            "classes": [],
            "riding_description": "",
            "coggins_status": "Missing",
            "crop": "Optional",
            "spurs": "Optional",
            "lead_change": "Either",
        }]}
        warnings = hoofprint_warnings(payload)
        self.assertIn("Scout does not have any show classes assigned.", warnings)
        self.assertIn("Scout is missing a rider-facing description.", warnings)
        self.assertIn("Scout has missing Coggins information.", warnings)

    def test_no_snapshot_is_not_reported_as_drift(self):
        self.assertFalse(live_differs_from_snapshot({"show": {}, "horses": []}, None))
