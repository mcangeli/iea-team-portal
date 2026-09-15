from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from portal.horse_models import Horse
from portal.model_modules.equine_care import HorseCareRecord
from portal.model_modules.people import Person
from portal.models import Team, UserProfile


User = get_user_model()


class EquineCareUiTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="ArenaLine Care UI")
        self.admin = User.objects.create_user(username="care-admin", password="test-pass-123")
        self.admin.profile.team = self.team
        self.admin.profile.role = UserProfile.Role.ADMIN
        self.admin.profile.save(update_fields=["team", "role"])
        self.horse = Horse.objects.create(team=self.team, name="Atlas")
        self.provider = Person.objects.create(team=self.team, first_name="Dana", last_name="Vet", active=True)
        self.client.force_login(self.admin)

    def test_manager_can_add_care_record(self):
        performed = timezone.localdate()
        response = self.client.post(reverse("horse_care_add", args=[self.horse.pk]), {
            "care_type": HorseCareRecord.CareType.VETERINARY,
            "title": "Annual wellness exam",
            "performed_date": performed.isoformat(),
            "next_due_date": (performed + timedelta(days=365)).isoformat(),
            "provider": self.provider.pk,
            "notes": "Routine annual visit.",
        })
        self.assertRedirects(response, reverse("horse_detail", args=[self.horse.pk]))
        record = HorseCareRecord.objects.get(horse=self.horse)
        self.assertEqual(record.title, "Annual wellness exam")
        self.assertEqual(record.provider, self.provider)

    def test_manager_can_edit_care_record(self):
        record = HorseCareRecord.objects.create(
            horse=self.horse,
            care_type=HorseCareRecord.CareType.FARRIER,
            title="Trim",
            performed_date=timezone.localdate(),
        )
        response = self.client.post(reverse("horse_care_edit", args=[self.horse.pk, record.pk]), {
            "care_type": HorseCareRecord.CareType.FARRIER,
            "title": "Trim and front shoes",
            "performed_date": record.performed_date.isoformat(),
            "next_due_date": "",
            "provider": "",
            "notes": "",
        })
        self.assertRedirects(response, reverse("horse_detail", args=[self.horse.pk]))
        record.refresh_from_db()
        self.assertEqual(record.title, "Trim and front shoes")

    def test_horse_profile_shows_care_history_and_due_status(self):
        HorseCareRecord.objects.create(
            horse=self.horse,
            care_type=HorseCareRecord.CareType.DENTAL,
            title="Dental float",
            performed_date=timezone.localdate() - timedelta(days=300),
            next_due_date=timezone.localdate() + timedelta(days=10),
            provider=self.provider,
        )
        response = self.client.get(reverse("horse_detail", args=[self.horse.pk]))
        self.assertContains(response, "Care history")
        self.assertContains(response, "Dental float")
        self.assertContains(response, "Due soon")
        self.assertContains(response, self.provider.display_name)

    def test_non_manager_does_not_see_care_history(self):
        viewer = User.objects.create_user(username="care-viewer", password="test-pass-123")
        viewer.profile.team = self.team
        viewer.profile.role = UserProfile.Role.RIDER
        viewer.profile.save(update_fields=["team", "role"])
        HorseCareRecord.objects.create(
            horse=self.horse,
            care_type=HorseCareRecord.CareType.VETERINARY,
            title="Private care note",
            performed_date=timezone.localdate(),
            notes="Sensitive operational detail",
        )
        self.client.force_login(viewer)
        response = self.client.get(reverse("horse_detail", args=[self.horse.pk]))
        self.assertNotContains(response, "Private care note")
        self.assertNotContains(response, "Sensitive operational detail")

    def test_non_manager_cannot_add_care_record(self):
        viewer = User.objects.create_user(username="care-rider", password="test-pass-123")
        viewer.profile.team = self.team
        viewer.profile.role = UserProfile.Role.RIDER
        viewer.profile.save(update_fields=["team", "role"])
        self.client.force_login(viewer)
        response = self.client.get(reverse("horse_care_add", args=[self.horse.pk]))
        self.assertEqual(response.status_code, 403)

    def test_cannot_edit_care_record_from_another_organization(self):
        other_team = Team.objects.create(name="Other Program")
        other_horse = Horse.objects.create(team=other_team, name="Comet")
        record = HorseCareRecord.objects.create(
            horse=other_horse,
            care_type=HorseCareRecord.CareType.FARRIER,
            title="Trim",
            performed_date=timezone.localdate(),
        )
        response = self.client.get(reverse("horse_care_edit", args=[other_horse.pk, record.pk]))
        self.assertEqual(response.status_code, 404)
