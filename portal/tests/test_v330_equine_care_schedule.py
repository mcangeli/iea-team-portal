from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from portal.equine_care_schedule import care_schedule_for_horse
from portal.horse_models import Horse
from portal.model_modules.equine_care import HorseCareRecord
from portal.models import Team


class EquineCareScheduleTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="ArenaLine Schedule Test")
        self.horse = Horse.objects.create(team=self.team, name="Atlas")
        self.today = timezone.localdate()

    def record(self, care_type, title, performed_days_ago, due_days_from_now=None):
        return HorseCareRecord.objects.create(
            horse=self.horse,
            care_type=care_type,
            title=title,
            performed_date=self.today - timedelta(days=performed_days_ago),
            next_due_date=(self.today + timedelta(days=due_days_from_now)) if due_days_from_now is not None else None,
        )

    def test_newer_record_supersedes_older_overdue_record_in_same_category(self):
        self.record(HorseCareRecord.CareType.FARRIER, "Old trim", 70, -20)
        newest = self.record(HorseCareRecord.CareType.FARRIER, "Fresh trim", 2, 40)
        schedule = care_schedule_for_horse(self.horse)
        self.assertEqual(schedule.items, (newest,))
        self.assertEqual(schedule.overall_status, "current")

    def test_schedule_orders_overdue_then_due_soon_then_current(self):
        overdue = self.record(HorseCareRecord.CareType.FARRIER, "Trim", 50, -2)
        soon = self.record(HorseCareRecord.CareType.DENTAL, "Dental", 300, 12)
        current = self.record(HorseCareRecord.CareType.VACCINATION, "Vaccines", 10, 180)
        schedule = care_schedule_for_horse(self.horse)
        self.assertEqual(schedule.items, (overdue, soon, current))
        self.assertEqual(schedule.overall_status, "overdue")

    def test_record_without_next_due_date_is_history_not_schedule(self):
        self.record(HorseCareRecord.CareType.VETERINARY, "One-time visit", 1)
        schedule = care_schedule_for_horse(self.horse)
        self.assertEqual(schedule.items, ())
        self.assertEqual(schedule.overall_status, "none")

    def test_urgent_items_include_only_overdue_and_due_soon(self):
        overdue = self.record(HorseCareRecord.CareType.FARRIER, "Trim", 50, -1)
        soon = self.record(HorseCareRecord.CareType.DENTAL, "Dental", 300, 10)
        self.record(HorseCareRecord.CareType.VACCINATION, "Vaccines", 5, 200)
        schedule = care_schedule_for_horse(self.horse)
        self.assertEqual(schedule.urgent_items, (overdue, soon))

    def test_coggins_is_not_a_generic_care_choice(self):
        values = {value for value, _label in HorseCareRecord.CareType.choices}
        self.assertNotIn("coggins", values)

    def test_due_soon_becomes_overall_status_when_nothing_is_overdue(self):
        self.record(HorseCareRecord.CareType.DENTAL, "Dental", 300, 10)
        self.record(HorseCareRecord.CareType.VACCINATION, "Vaccines", 5, 200)
        schedule = care_schedule_for_horse(self.horse)
        self.assertEqual(schedule.overall_status, "due_soon")
        self.assertEqual(schedule.overall_status_label, "Care due soon")
