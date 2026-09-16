from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from portal.hoofprint_models import HoofprintSnapshot
from portal.horse_models import Horse, HorseCogginsRecord, HorseShowAssignment
from portal.model_modules.equine_compliance_requirements import HorseComplianceRequirement
from portal.model_modules.equine_documents import HorseDocument
from portal.models import Season, Show, Team, UserProfile

User = get_user_model()


class EquineHoofprintComplianceTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="ArenaLine Hoofprint Compliance")
        self.season = Season.objects.create(
            team=self.team,
            name="2026-27",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 6, 30),
            is_active=True,
        )
        self.show = Show.objects.create(
            team=self.team,
            season=self.season,
            name="Autumn Hoofprint Show",
            show_date=date(2026, 10, 1),
        )
        self.horse = Horse.objects.create(team=self.team, name="Atlas")
        self.assignment = HorseShowAssignment.objects.create(
            show=self.show,
            horse=self.horse,
            available=True,
        )
        self.admin = User.objects.create_user(username="hoofprint-compliance-admin", password="test-pass-123")
        self.admin.profile.team = self.team
        self.admin.profile.role = UserProfile.Role.ADMIN
        self.admin.profile.save(update_fields=["team", "role"])
        self.client.force_login(self.admin)

    def _file(self):
        return SimpleUploadedFile("registration.pdf", b"ArenaLine", content_type="application/pdf")

    def _finalize_data(self):
        return {
            "coach_name": "Coach ArenaLine",
            "coach_phone": "555-0100",
            "horses_contributed": 1,
            "notes": "Ready for submission",
        }

    def test_builder_surfaces_exact_blocking_requirement(self):
        HorseComplianceRequirement.objects.create(
            team=self.team,
            name="Registration papers",
            requirement_type="document",
            document_type="registration",
        )

        response = self.client.get(reverse("show_hoofprint", args=[self.show.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SHOW COMPLIANCE")
        self.assertContains(response, "Compliance must be resolved before finalizing")
        self.assertContains(response, "Registration papers — Missing")
        self.assertContains(response, "disabled")

    def test_server_blocks_finalize_and_creates_no_snapshot(self):
        HorseComplianceRequirement.objects.create(
            team=self.team,
            name="Registration papers",
            requirement_type="document",
            document_type="registration",
        )

        response = self.client.post(
            reverse("show_hoofprint_finalize", args=[self.show.pk]),
            self._finalize_data(),
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(HoofprintSnapshot.objects.filter(show=self.show).count(), 0)
        self.assertContains(
            response,
            "Hoofprint cannot be finalized while a required horse compliance item is missing, expired, or will not remain valid through the show date.",
            status_code=400,
        )

    def test_record_expiring_before_show_blocks_finalize(self):
        HorseComplianceRequirement.objects.create(
            team=self.team,
            name="Registration papers",
            requirement_type="document",
            document_type="registration",
        )
        today = timezone.localdate()
        self.show.show_date = today + timedelta(days=90)
        self.show.save(update_fields=["show_date"])
        HorseDocument.objects.create(
            horse=self.horse,
            document_type="registration",
            title="Registration",
            file=self._file(),
            expiration_date=today + timedelta(days=60),
        )

        page = self.client.get(reverse("show_hoofprint", args=[self.show.pk]))
        response = self.client.post(reverse("show_hoofprint_finalize", args=[self.show.pk]), self._finalize_data())

        self.assertContains(page, "Registration papers — Not valid through date")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(HoofprintSnapshot.objects.filter(show=self.show).exists())

    def test_expiring_soon_warning_does_not_block_finalize(self):
        HorseComplianceRequirement.objects.create(
            team=self.team,
            name="Current Coggins",
            requirement_type="coggins",
        )
        today = timezone.localdate()
        expiration = today + timedelta(days=10)
        self.show.show_date = today + timedelta(days=5)
        self.show.save(update_fields=["show_date"])
        HorseCogginsRecord.objects.create(
            horse=self.horse,
            test_date=today,
            expiration_date=expiration,
        )

        page = self.client.get(reverse("show_hoofprint", args=[self.show.pk]))
        response = self.client.post(reverse("show_hoofprint_finalize", args=[self.show.pk]), self._finalize_data())

        self.assertContains(page, "Current Coggins — Expiring soon")
        self.assertNotContains(page, "Compliance must be resolved before finalizing")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(HoofprintSnapshot.objects.filter(show=self.show).count(), 1)

    def test_expiration_on_show_date_allows_finalize(self):
        HorseComplianceRequirement.objects.create(
            team=self.team,
            name="Current Coggins",
            requirement_type="coggins",
        )
        today = timezone.localdate()
        self.show.show_date = today + timedelta(days=60)
        self.show.save(update_fields=["show_date"])
        HorseCogginsRecord.objects.create(
            horse=self.horse,
            test_date=today,
            expiration_date=self.show.show_date,
        )

        response = self.client.post(reverse("show_hoofprint_finalize", args=[self.show.pk]), self._finalize_data())

        self.assertEqual(response.status_code, 302)
        self.assertEqual(HoofprintSnapshot.objects.filter(show=self.show).count(), 1)

    def test_non_manager_does_not_see_private_compliance_details(self):
        HorseComplianceRequirement.objects.create(
            team=self.team,
            name="Private insurance requirement",
            requirement_type="document",
            document_type="insurance",
        )
        rider = User.objects.create_user(username="hoofprint-compliance-rider", password="test-pass-123")
        rider.profile.team = self.team
        rider.profile.role = UserProfile.Role.RIDER
        rider.profile.save(update_fields=["team", "role"])
        self.client.force_login(rider)

        response = self.client.get(reverse("show_hoofprint", args=[self.show.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "SHOW COMPLIANCE")
        self.assertNotContains(response, "Private insurance requirement")
