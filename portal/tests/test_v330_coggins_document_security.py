from datetime import timedelta

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from portal.horse_models import Horse, HorseCogginsRecord
from portal.models import Team, UserProfile


class CogginsDocumentSecurityTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Coggins Security")
        self.other_team = Team.objects.create(name="Other Coggins Security")
        self.admin = User.objects.create_user("coggins-admin", password="testpass123")
        self.admin.profile.team = self.team
        self.admin.profile.role = UserProfile.Role.ADMIN
        self.admin.profile.save(update_fields=["team", "role"])
        self.rider = User.objects.create_user("coggins-rider", password="testpass123")
        self.rider.profile.team = self.team
        self.rider.profile.role = UserProfile.Role.RIDER
        self.rider.profile.save(update_fields=["team", "role"])
        self.horse = Horse.objects.create(team=self.team, name="Biscuit")
        today = timezone.localdate()
        self.record = HorseCogginsRecord.objects.create(
            horse=self.horse,
            test_date=today - timedelta(days=30),
            expiration_date=today + timedelta(days=300),
            document=SimpleUploadedFile("biscuit-coggins.pdf", b"coggins document", content_type="application/pdf"),
        )

    def test_manager_can_open_coggins_through_protected_endpoint(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("horse_coggins_document", args=[self.horse.pk, self.record.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(response["Pragma"], "no-cache")

    def test_profile_uses_protected_coggins_link_not_media_url(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("horse_detail", args=[self.horse.pk]))
        self.assertContains(response, reverse("horse_coggins_document", args=[self.horse.pk, self.record.pk]))
        self.assertNotContains(response, self.record.document.url)

    def test_non_manager_cannot_open_coggins_document(self):
        self.client.force_login(self.rider)
        response = self.client.get(reverse("horse_coggins_document", args=[self.horse.pk, self.record.pk]))
        self.assertEqual(response.status_code, 403)

    def test_other_organization_coggins_is_not_discoverable(self):
        other_horse = Horse.objects.create(team=self.other_team, name="Comet")
        today = timezone.localdate()
        other_record = HorseCogginsRecord.objects.create(
            horse=other_horse,
            test_date=today - timedelta(days=30),
            expiration_date=today + timedelta(days=300),
            document=SimpleUploadedFile("comet-coggins.pdf", b"other coggins", content_type="application/pdf"),
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse("horse_coggins_document", args=[other_horse.pk, other_record.pk]))
        self.assertEqual(response.status_code, 404)

    def test_record_without_document_returns_not_found(self):
        today = timezone.localdate()
        empty_record = HorseCogginsRecord.objects.create(
            horse=self.horse,
            test_date=today - timedelta(days=60),
            expiration_date=today + timedelta(days=200),
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse("horse_coggins_document", args=[self.horse.pk, empty_record.pk]))
        self.assertEqual(response.status_code, 404)
