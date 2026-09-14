from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class ArenaLinePreview4OperationsTests(SimpleTestCase):
    def test_base_loads_operations_presentation_layer(self):
        base = (Path(settings.BASE_DIR) / "templates/base.html").read_text()
        self.assertIn("css/operations-v290.css", base)

    def test_operations_layer_covers_core_surfaces(self):
        css = (Path(settings.BASE_DIR) / "static/css/operations-v290.css").read_text()
        for selector in (
            ".action-row",
            ".ops-row",
            ".volunteer-card",
            ".committee-card",
            ".section-calendar .calendar-toolbar",
            ".section-calendar .month-calendar",
            ".notification-nav .notification-count",
        ):
            self.assertIn(selector, css)

    def test_operations_workflow_semantics_remain_in_templates(self):
        actions = (Path(settings.BASE_DIR) / "templates/portal/action_item_list.html").read_text()
        lessons = (Path(settings.BASE_DIR) / "templates/portal/lesson_list.html").read_text()
        volunteer = (Path(settings.BASE_DIR) / "templates/portal/volunteer_dashboard.html").read_text()
        committees = (Path(settings.BASE_DIR) / "templates/portal/committee_list.html").read_text()

        self.assertIn("action_item_claim", actions)
        self.assertIn("action_item_complete", actions)
        self.assertIn("lesson_detail", lessons)
        self.assertIn("Only approved hours count", volunteer)
        self.assertIn("volunteer_review", volunteer)
        self.assertIn("Delegated, not administrative", committees)

    def test_calendar_presentation_is_owned_by_operations_stylesheet(self):
        calendar = (Path(settings.BASE_DIR) / "templates/portal/calendar_v2.html").read_text()
        css = (Path(settings.BASE_DIR) / "static/css/operations-v290.css").read_text()

        self.assertNotIn("<style>", calendar)
        for selector in (
            ".section-calendar .calendar-toolbar",
            ".section-calendar .calendar-period-nav",
            ".section-calendar .calendar-view-switch",
            ".section-calendar .calendar-filters",
            ".section-calendar .month-grid",
            ".section-calendar .agenda-event",
        ):
            self.assertIn(selector, css)
