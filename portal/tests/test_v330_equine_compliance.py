from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from portal.equine_compliance import compliance_summary_for_horse
from portal.horse_models import Horse, HorseCogginsRecord
from portal.model_modules.equine_documents import HorseDocument
from portal.models import Team, UserProfile


User = get_user_model()


class EquineComplianceTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="ArenaLine Compliance")
        self.admin = User.objects.create_user(username="compliance-admin", password="test-pass-123")
        self.admin.profile.team = self.team
        self.admin.profile.role = UserProfile.Role.ADMIN
        self.admin.profile.save(update_fields=["team", "role"])
        self.horse = Horse.objects.create(team=self.team, name="Atlas")
        self.client.force_login(self.admin)

    def _file(self, name="document.pdf"):
        return SimpleUploadedFile(name, b"ArenaLine compliance test", content_type="application/pdf")

    def test_missing_coggins_requires_attention(self):
        summary = compliance_summary_for_horse(self.horse)
        self.assertEqual(summary.overall_status, "attention")
        self.assertEqual(summary.items[0].label, "Coggins")
        self.assertEqual(summary.items[0].status_label, "Missing")

    def test_expiring_coggins_creates_warning(self):
        today = timezone.localdate()
        HorseCogginsRecord.objects.create(horse=self.horse, test_date=today - timedelta(days=300), expiration_date=today + timedelta(days=10))
        summary = compliance_summary_for_horse(self.horse)
        self.assertEqual(summary.overall_status, "warning")
        self.assertEqual(summary.items[0].status_label, "Expiring soon")

    def test_expired_generic_document_requires_attention(self):
        today = timezone.localdate()
        HorseCogginsRecord.objects.create(horse=self.horse, test_date=today, expiration_date=today + timedelta(days=365))
        HorseDocument.objects.create(horse=self.horse, document_type=HorseDocument.DocumentType.LEASE, title="Lease agreement", file=self._file(), expiration_date=today - timedelta(days=1))
        summary = compliance_summary_for_horse(self.horse)
        self.assertEqual(summary.overall_status, "attention")
        self.assertTrue(any(item.label == "Lease agreement" and item.status_label == "Expired" for item in summary.items))

    def test_current_and_nonexpiring_documents_do_not_create_alerts(self):
        today = timezone.localdate()
        HorseCogginsRecord.objects.create(horse=self.horse, test_date=today, expiration_date=today + timedelta(days=365))
        HorseDocument.objects.create(horse=self.horse, document_type=HorseDocument.DocumentType.REGISTRATION, title="Registration", file=self._file(), expiration_date=today + timedelta(days=90))
        HorseDocument.objects.create(horse=self.horse, document_type=HorseDocument.DocumentType.OWNERSHIP, title="Bill of sale", file=self._file("ownership.pdf"))
        summary = compliance_summary_for_horse(self.horse)
        self.assertEqual(summary.overall_status, "current")
        self.assertEqual(len(summary.items), 1)
        self.assertEqual(summary.items[0].label, "Coggins")

    def test_manager_profile_shows_compliance_summary(self):
        response = self.client.get(reverse("horse_detail", args=[self.horse.pk]))
        self.assertContains(response, "COMPLIANCE STATUS")
        self.assertContains(response, "Compliance attention needed")
        self.assertContains(response, "No Coggins record on file")

    def test_manager_registry_shows_combined_compliance_status(self):
        response = self.client.get(reverse("horse_list"))
        self.assertContains(response, "Compliance:")
        self.assertContains(response, "Compliance attention needed")
        self.assertContains(response, "Coggins — Missing")

    def test_non_manager_registry_keeps_existing_coggins_view_without_private_documents(self):
        HorseDocument.objects.create(horse=self.horse, document_type=HorseDocument.DocumentType.VETERINARY, title="Private vet paperwork", file=self._file())
        rider = User.objects.create_user(username="compliance-rider", password="test-pass-123")
        rider.profile.team = self.team
        rider.profile.role = UserProfile.Role.RIDER
        rider.profile.save(update_fields=["team", "role"])
        self.client.force_login(rider)
        response = self.client.get(reverse("horse_list"))
        self.assertContains(response, "Coggins:")
        self.assertContains(response, "No Coggins on file")
        self.assertNotContains(response, "Compliance:")
        self.assertNotContains(response, "Private vet paperwork")
