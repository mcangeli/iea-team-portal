from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from portal.equine_compliance import compliance_summary_for_horse
from portal.horse_models import Horse, HorseCogginsRecord, HorseShowAssignment
from portal.model_modules.equine_compliance_requirements import HorseComplianceRequirement
from portal.model_modules.equine_documents import HorseDocument
from portal.models import Season, Show, Team, UserProfile
from portal.show_readiness_service import build_show_readiness

User = get_user_model()


class EquineShowComplianceTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="ArenaLine Show Compliance")
        self.season = Season.objects.create(team=self.team, name="2026-27", start_date=date(2026, 8, 1), end_date=date(2027, 6, 30), is_active=True)
        self.show = Show.objects.create(team=self.team, season=self.season, name="Autumn Show", show_date=date(2026, 10, 1))
        self.horse = Horse.objects.create(team=self.team, name="Atlas")
        self.assignment = HorseShowAssignment.objects.create(show=self.show, horse=self.horse, available=True)
        self.admin = User.objects.create_user(username="show-compliance-admin", password="test-pass-123")
        self.admin.profile.team = self.team; self.admin.profile.role = UserProfile.Role.ADMIN; self.admin.profile.save(update_fields=["team", "role"])
        self.client.force_login(self.admin)

    def _file(self):
        return SimpleUploadedFile("registration.pdf", b"ArenaLine", content_type="application/pdf")

    def test_missing_required_document_blocks_show_readiness(self):
        HorseComplianceRequirement.objects.create(team=self.team, name="Registration papers", requirement_type="document", document_type="registration")
        readiness = build_show_readiness(self.show)
        self.assertFalse(readiness["compliance_ready"])
        self.assertFalse(readiness["ready"])
        self.assertEqual(readiness["compliance_warning_count"], 1)
        self.assertEqual(readiness["compliance_warnings"][0]["summary"].items[0].status_label, "Missing")

    def test_expiring_requirement_warns_without_blocking_readiness(self):
        HorseComplianceRequirement.objects.create(team=self.team, name="Registration papers", requirement_type="document", document_type="registration")
        expiration = max(timezone.localdate() + timedelta(days=10), self.show.show_date)
        HorseDocument.objects.create(horse=self.horse, document_type="registration", title="Registration", file=self._file(), expiration_date=expiration)
        readiness = build_show_readiness(self.show)
        self.assertTrue(readiness["compliance_ready"])
        self.assertTrue(readiness["ready"])
        if expiration <= timezone.localdate() + timedelta(days=30):
            self.assertEqual(readiness["compliance_warning_count"], 1)

    def test_current_requirements_allow_show_readiness(self):
        HorseComplianceRequirement.objects.create(team=self.team, name="Current Coggins", requirement_type="coggins")
        today = timezone.localdate()
        HorseCogginsRecord.objects.create(horse=self.horse, test_date=today, expiration_date=max(today + timedelta(days=365), self.show.show_date))
        readiness = build_show_readiness(self.show)
        self.assertTrue(readiness["compliance_ready"])
        self.assertTrue(readiness["ready"])
        self.assertEqual(readiness["compliance_warning_count"], 0)

    def test_document_current_today_but_expiring_before_show_blocks_readiness(self):
        HorseComplianceRequirement.objects.create(team=self.team, name="Registration papers", requirement_type="document", document_type="registration")
        today = timezone.localdate()
        future_show_date = today + timedelta(days=90)
        self.show.show_date = future_show_date
        self.show.save(update_fields=["show_date"])
        HorseDocument.objects.create(horse=self.horse, document_type="registration", title="Registration", file=self._file(), expiration_date=today + timedelta(days=60))

        registry_summary = compliance_summary_for_horse(self.horse)
        readiness = build_show_readiness(self.show)

        self.assertEqual(registry_summary.overall_status, "current")
        self.assertFalse(readiness["compliance_ready"])
        self.assertFalse(readiness["ready"])
        self.assertEqual(readiness["compliance_warnings"][0]["summary"].items[0].status_label, "Not valid through date")

    def test_coggins_current_today_but_expiring_before_show_blocks_readiness(self):
        HorseComplianceRequirement.objects.create(team=self.team, name="Current Coggins", requirement_type="coggins")
        today = timezone.localdate()
        self.show.show_date = today + timedelta(days=90)
        self.show.save(update_fields=["show_date"])
        HorseCogginsRecord.objects.create(horse=self.horse, test_date=today, expiration_date=today + timedelta(days=60))

        readiness = build_show_readiness(self.show)

        self.assertFalse(readiness["compliance_ready"])
        self.assertEqual(readiness["compliance_warnings"][0]["summary"].items[0].status_label, "Not valid through date")

    def test_expiration_on_show_date_is_valid(self):
        HorseComplianceRequirement.objects.create(team=self.team, name="Current Coggins", requirement_type="coggins")
        today = timezone.localdate()
        self.show.show_date = today + timedelta(days=90)
        self.show.save(update_fields=["show_date"])
        HorseCogginsRecord.objects.create(horse=self.horse, test_date=today, expiration_date=self.show.show_date)

        readiness = build_show_readiness(self.show)

        self.assertTrue(readiness["compliance_ready"])
        self.assertTrue(readiness["ready"])

    def test_show_readiness_page_lists_exact_missing_requirement(self):
        HorseComplianceRequirement.objects.create(team=self.team, name="Registration papers", requirement_type="document", document_type="registration")
        response = self.client.get(reverse("show_readiness", args=[self.show.pk]))
        self.assertContains(response, "COMPLIANCE CHECK")
        self.assertContains(response, "Registration papers — Missing")
        self.assertContains(response, "Horse plan needs attention")

    def test_show_horse_card_shows_compliance_status_to_manager(self):
        HorseComplianceRequirement.objects.create(team=self.team, name="Registration papers", requirement_type="document", document_type="registration")
        response = self.client.get(reverse("show_horses", args=[self.show.pk]))
        self.assertContains(response, "Compliance:")
        self.assertContains(response, "Needs attention")
        self.assertContains(response, "Registration papers — Missing")

    def test_show_horse_card_uses_show_date_for_compliance(self):
        HorseComplianceRequirement.objects.create(team=self.team, name="Registration papers", requirement_type="document", document_type="registration")
        today = timezone.localdate()
        self.show.show_date = today + timedelta(days=90)
        self.show.save(update_fields=["show_date"])
        HorseDocument.objects.create(horse=self.horse, document_type="registration", title="Registration", file=self._file(), expiration_date=today + timedelta(days=60))

        response = self.client.get(reverse("show_horses", args=[self.show.pk]))

        self.assertContains(response, "Needs attention")
        self.assertContains(response, "Registration papers — Not valid through date")

    def test_rider_show_horse_card_retains_coggins_only_view(self):
        HorseComplianceRequirement.objects.create(team=self.team, name="Private insurance", requirement_type="document", document_type="insurance")
        rider = User.objects.create_user(username="show-compliance-rider", password="test-pass-123")
        rider.profile.team = self.team; rider.profile.role = UserProfile.Role.RIDER; rider.profile.save(update_fields=["team", "role"])
        self.client.force_login(rider)
        response = self.client.get(reverse("show_horses", args=[self.show.pk]))
        self.assertContains(response, "Coggins:")
        self.assertNotContains(response, "Private insurance")
        self.assertNotContains(response, "Compliance:")
