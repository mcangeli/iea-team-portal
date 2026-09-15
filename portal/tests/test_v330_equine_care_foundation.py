from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from portal.horse_models import Horse
from portal.model_modules.equine_care import HorseCareRecord
from portal.model_modules.people import Person
from portal.models import Team


class EquineCareFoundationTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="ArenaLine Test Program")
        self.horse = Horse.objects.create(team=self.team, name="Atlas")
        self.provider = Person.objects.create(team=self.team, first_name="Dana", last_name="Vet", active=True)

    def test_care_record_preserves_historical_event(self):
        performed = timezone.localdate() - timedelta(days=14)
        due = performed + timedelta(days=365)
        record = HorseCareRecord.objects.create(
            horse=self.horse,
            care_type=HorseCareRecord.CareType.VACCINATION,
            title="Spring vaccines",
            performed_date=performed,
            next_due_date=due,
            provider=self.provider,
        )
        self.assertEqual(record.horse, self.horse)
        self.assertEqual(record.provider, self.provider)
        self.assertEqual(record.next_due_date, due)
        self.assertEqual(self.horse.care_records.get(), record)

    def test_care_types_cover_core_operational_categories(self):
        values = dict(HorseCareRecord.CareType.choices)
        self.assertEqual(values[HorseCareRecord.CareType.VACCINATION], "Vaccination")
        self.assertEqual(values[HorseCareRecord.CareType.FARRIER], "Farrier")
        self.assertEqual(values[HorseCareRecord.CareType.DENTAL], "Dental")
        self.assertEqual(values[HorseCareRecord.CareType.VETERINARY], "Veterinary visit")
        self.assertEqual(values[HorseCareRecord.CareType.MEDICATION], "Medication / treatment")

    def test_provider_must_belong_to_horse_organization(self):
        other_team = Team.objects.create(name="Other Barn")
        outsider = Person.objects.create(team=other_team, first_name="Outside", last_name="Vet", active=True)
        record = HorseCareRecord(
            horse=self.horse,
            care_type=HorseCareRecord.CareType.VETERINARY,
            title="Annual exam",
            performed_date=timezone.localdate(),
            provider=outsider,
        )
        with self.assertRaises(ValidationError):
            record.full_clean()

    def test_next_due_date_cannot_precede_performed_date(self):
        today = timezone.localdate()
        record = HorseCareRecord(
            horse=self.horse,
            care_type=HorseCareRecord.CareType.FARRIER,
            title="Trim",
            performed_date=today,
            next_due_date=today - timedelta(days=1),
        )
        with self.assertRaises(ValidationError):
            record.full_clean()

    def test_due_status_reports_overdue_due_soon_and_current(self):
        today = timezone.localdate()
        overdue = HorseCareRecord(horse=self.horse, care_type="farrier", title="Trim", performed_date=today - timedelta(days=60), next_due_date=today - timedelta(days=1))
        soon = HorseCareRecord(horse=self.horse, care_type="dental", title="Dental", performed_date=today - timedelta(days=300), next_due_date=today + timedelta(days=15))
        current = HorseCareRecord(horse=self.horse, care_type="vaccination", title="Vaccines", performed_date=today, next_due_date=today + timedelta(days=180))
        no_due = HorseCareRecord(horse=self.horse, care_type="other", title="Note", performed_date=today)
        self.assertEqual(overdue.due_status, "overdue")
        self.assertEqual(soon.due_status, "due_soon")
        self.assertEqual(current.due_status, "current")
        self.assertEqual(no_due.due_status, "none")

    def test_deleting_provider_preserves_care_history(self):
        record = HorseCareRecord.objects.create(
            horse=self.horse,
            care_type=HorseCareRecord.CareType.DENTAL,
            title="Dental float",
            performed_date=timezone.localdate(),
            provider=self.provider,
        )
        self.provider.delete()
        record.refresh_from_db()
        self.assertIsNone(record.provider)
        self.assertEqual(record.title, "Dental float")

    def test_deleting_horse_removes_its_care_records(self):
        HorseCareRecord.objects.create(
            horse=self.horse,
            care_type=HorseCareRecord.CareType.FARRIER,
            title="Front shoes",
            performed_date=timezone.localdate(),
        )
        self.horse.delete()
        self.assertFalse(HorseCareRecord.objects.exists())
