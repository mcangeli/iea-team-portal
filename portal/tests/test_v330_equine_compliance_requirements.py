from datetime import timedelta

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from portal.equine_compliance import compliance_summary_for_horse
from portal.horse_models import Horse, HorseCogginsRecord
from portal.model_modules.equine_compliance_requirements import HorseComplianceRequirement
from portal.model_modules.equine_documents import HorseDocument
from portal.models import Team


class EquineComplianceRequirementTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="ArenaLine Requirements")
        self.horse = Horse.objects.create(team=self.team, name="Atlas")

    def _file(self, name="document.pdf"):
        return SimpleUploadedFile(name, b"ArenaLine requirement test", content_type="application/pdf")

    def test_document_requirement_requires_document_type(self):
        requirement = HorseComplianceRequirement(team=self.team, name="Registration", requirement_type=HorseComplianceRequirement.RequirementType.DOCUMENT)
        with self.assertRaises(ValidationError):
            requirement.full_clean()

    def test_coggins_requirement_does_not_accept_document_type(self):
        requirement = HorseComplianceRequirement(team=self.team, name="Coggins", requirement_type=HorseComplianceRequirement.RequirementType.COGGINS, document_type=HorseDocument.DocumentType.REGISTRATION)
        with self.assertRaises(ValidationError):
            requirement.full_clean()

    def test_missing_required_document_requires_attention(self):
        HorseComplianceRequirement.objects.create(team=self.team, name="Registration papers", requirement_type=HorseComplianceRequirement.RequirementType.DOCUMENT, document_type=HorseDocument.DocumentType.REGISTRATION)
        summary = compliance_summary_for_horse(self.horse)
        self.assertTrue(summary.requirements_configured)
        self.assertEqual(summary.overall_status, "attention")
        self.assertEqual(summary.items[0].status_label, "Missing")

    def test_current_required_document_satisfies_requirement(self):
        HorseComplianceRequirement.objects.create(team=self.team, name="Registration papers", requirement_type=HorseComplianceRequirement.RequirementType.DOCUMENT, document_type=HorseDocument.DocumentType.REGISTRATION)
        HorseDocument.objects.create(horse=self.horse, document_type=HorseDocument.DocumentType.REGISTRATION, title="USEF registration", file=self._file(), expiration_date=timezone.localdate() + timedelta(days=90))
        summary = compliance_summary_for_horse(self.horse)
        self.assertEqual(summary.overall_status, "current")
        self.assertEqual(summary.items[0].status_label, "Current")

    def test_expiring_required_document_warns(self):
        HorseComplianceRequirement.objects.create(team=self.team, name="Lease paperwork", requirement_type=HorseComplianceRequirement.RequirementType.DOCUMENT, document_type=HorseDocument.DocumentType.LEASE)
        HorseDocument.objects.create(horse=self.horse, document_type=HorseDocument.DocumentType.LEASE, title="Season lease", file=self._file(), expiration_date=timezone.localdate() + timedelta(days=10))
        summary = compliance_summary_for_horse(self.horse)
        self.assertEqual(summary.overall_status, "warning")
        self.assertEqual(summary.items[0].status_label, "Expiring soon")

    def test_dedicated_coggins_requirement_uses_coggins_record(self):
        HorseComplianceRequirement.objects.create(team=self.team, name="Current Coggins", requirement_type=HorseComplianceRequirement.RequirementType.COGGINS)
        today = timezone.localdate()
        HorseCogginsRecord.objects.create(horse=self.horse, test_date=today, expiration_date=today + timedelta(days=365))
        summary = compliance_summary_for_horse(self.horse)
        self.assertEqual(summary.overall_status, "current")
        self.assertEqual(summary.items[0].label, "Current Coggins")
        self.assertEqual(summary.items[0].status_label, "Current")

    def test_inactive_requirement_is_not_enforced(self):
        HorseComplianceRequirement.objects.create(team=self.team, name="Insurance", requirement_type=HorseComplianceRequirement.RequirementType.DOCUMENT, document_type=HorseDocument.DocumentType.INSURANCE, active=False)
        summary = compliance_summary_for_horse(self.horse)
        self.assertFalse(summary.requirements_configured)
        self.assertEqual(summary.items[0].label, "Coggins")

    def test_requirements_are_organization_scoped(self):
        other_team = Team.objects.create(name="Other Barn")
        HorseComplianceRequirement.objects.create(team=other_team, name="Registration", requirement_type=HorseComplianceRequirement.RequirementType.DOCUMENT, document_type=HorseDocument.DocumentType.REGISTRATION)
        summary = compliance_summary_for_horse(self.horse)
        self.assertFalse(summary.requirements_configured)
        self.assertFalse(any(item.label == "Registration" for item in summary.items))
