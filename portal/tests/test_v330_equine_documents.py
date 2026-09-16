from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from portal.horse_models import Horse
from portal.model_modules.equine_care import HorseCareRecord
from portal.model_modules.equine_documents import HorseDocument
from portal.models import Team, UserProfile


User = get_user_model()


class EquineDocumentTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="ArenaLine Documents")
        self.admin = User.objects.create_user(username="document-admin", password="test-pass-123")
        self.admin.profile.team = self.team
        self.admin.profile.role = UserProfile.Role.ADMIN
        self.admin.profile.save(update_fields=["team", "role"])
        self.horse = Horse.objects.create(team=self.team, name="Atlas")
        self.client.force_login(self.admin)

    def _file(self, name="record.pdf"):
        return SimpleUploadedFile(name, b"ArenaLine test document", content_type="application/pdf")

    def test_manager_can_upload_document(self):
        today = timezone.localdate()
        response = self.client.post(reverse("horse_document_add", args=[self.horse.pk]), {
            "document_type": HorseDocument.DocumentType.REGISTRATION,
            "title": "USEF registration",
            "file": self._file(),
            "effective_date": today.isoformat(),
            "expiration_date": "",
            "care_record": "",
            "notes": "Current registration paperwork.",
        })
        self.assertRedirects(response, reverse("horse_detail", args=[self.horse.pk]))
        document = HorseDocument.objects.get(horse=self.horse)
        self.assertEqual(document.title, "USEF registration")

    def test_document_can_link_to_same_horse_care_record(self):
        care = HorseCareRecord.objects.create(horse=self.horse, care_type=HorseCareRecord.CareType.VACCINATION, title="Spring vaccines", performed_date=timezone.localdate())
        document = HorseDocument.objects.create(horse=self.horse, document_type=HorseDocument.DocumentType.VACCINATION, title="Vaccine certificate", file=self._file("vaccines.pdf"), care_record=care)
        self.assertEqual(document.care_record, care)
        self.assertEqual(list(care.documents.all()), [document])

    def test_document_rejects_care_record_from_other_horse(self):
        other = Horse.objects.create(team=self.team, name="Comet")
        care = HorseCareRecord.objects.create(horse=other, care_type=HorseCareRecord.CareType.FARRIER, title="Trim", performed_date=timezone.localdate())
        document = HorseDocument(horse=self.horse, document_type=HorseDocument.DocumentType.CARE, title="Wrong horse", file=self._file(), care_record=care)
        with self.assertRaises(ValidationError):
            document.full_clean()

    def test_expiration_statuses(self):
        today = timezone.localdate()
        expired = HorseDocument(horse=self.horse, document_type=HorseDocument.DocumentType.INSURANCE, title="Expired", file=self._file("expired.pdf"), expiration_date=today - timedelta(days=1))
        soon = HorseDocument(horse=self.horse, document_type=HorseDocument.DocumentType.LEASE, title="Soon", file=self._file("soon.pdf"), expiration_date=today + timedelta(days=10))
        current = HorseDocument(horse=self.horse, document_type=HorseDocument.DocumentType.REGISTRATION, title="Current", file=self._file("current.pdf"), expiration_date=today + timedelta(days=60))
        self.assertEqual(expired.expiration_status, "expired")
        self.assertEqual(soon.expiration_status, "expiring")
        self.assertEqual(current.expiration_status, "current")

    def test_profile_shows_documents_for_manager(self):
        document = HorseDocument.objects.create(horse=self.horse, document_type=HorseDocument.DocumentType.REGISTRATION, title="Registration papers", file=self._file())
        response = self.client.get(reverse("horse_detail", args=[self.horse.pk]))
        self.assertContains(response, "DOCUMENTS &amp; COMPLIANCE")
        self.assertContains(response, "Horse documents")
        self.assertContains(response, "Registration papers")
        self.assertContains(response, "Add document")
        self.assertContains(response, reverse("horse_document_download", args=[self.horse.pk, document.pk]))
        self.assertNotContains(response, document.file.url)

    def test_non_manager_does_not_see_general_documents(self):
        HorseDocument.objects.create(horse=self.horse, document_type=HorseDocument.DocumentType.VETERINARY, title="Private veterinary document", file=self._file())
        rider = User.objects.create_user(username="document-rider", password="test-pass-123")
        rider.profile.team = self.team
        rider.profile.role = UserProfile.Role.RIDER
        rider.profile.save(update_fields=["team", "role"])
        self.client.force_login(rider)
        response = self.client.get(reverse("horse_detail", args=[self.horse.pk]))
        self.assertNotContains(response, "Private veterinary document")
        self.assertNotContains(response, "DOCUMENTS &amp; COMPLIANCE")

    def test_non_manager_cannot_add_document(self):
        rider = User.objects.create_user(username="document-rider-add", password="test-pass-123")
        rider.profile.team = self.team
        rider.profile.role = UserProfile.Role.RIDER
        rider.profile.save(update_fields=["team", "role"])
        self.client.force_login(rider)
        response = self.client.get(reverse("horse_document_add", args=[self.horse.pk]))
        self.assertEqual(response.status_code, 403)

    def test_cannot_edit_document_from_another_organization(self):
        other_team = Team.objects.create(name="Other Barn")
        other_horse = Horse.objects.create(team=other_team, name="Comet")
        document = HorseDocument.objects.create(horse=other_horse, document_type=HorseDocument.DocumentType.OTHER, title="Other barn document", file=self._file())
        response = self.client.get(reverse("horse_document_edit", args=[other_horse.pk, document.pk]))
        self.assertEqual(response.status_code, 404)

    def test_manager_can_download_document_through_protected_endpoint(self):
        document = HorseDocument.objects.create(horse=self.horse, document_type=HorseDocument.DocumentType.VETERINARY, title="Veterinary record", file=self._file("vet.pdf"))
        response = self.client.get(reverse("horse_document_download", args=[self.horse.pk, document.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(response["Pragma"], "no-cache")

    def test_non_manager_cannot_download_document(self):
        document = HorseDocument.objects.create(horse=self.horse, document_type=HorseDocument.DocumentType.INSURANCE, title="Insurance", file=self._file("insurance.pdf"))
        rider = User.objects.create_user(username="document-rider-download", password="test-pass-123")
        rider.profile.team = self.team
        rider.profile.role = UserProfile.Role.RIDER
        rider.profile.save(update_fields=["team", "role"])
        self.client.force_login(rider)
        response = self.client.get(reverse("horse_document_download", args=[self.horse.pk, document.pk]))
        self.assertEqual(response.status_code, 403)

    def test_other_organization_document_download_is_not_discoverable(self):
        other_team = Team.objects.create(name="Other Download Barn")
        other_horse = Horse.objects.create(team=other_team, name="Comet")
        document = HorseDocument.objects.create(horse=other_horse, document_type=HorseDocument.DocumentType.VETERINARY, title="Other vet record", file=self._file("other-vet.pdf"))
        response = self.client.get(reverse("horse_document_download", args=[other_horse.pk, document.pk]))
        self.assertEqual(response.status_code, 404)
