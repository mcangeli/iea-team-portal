from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.equine_compliance_requirements import HorseComplianceRequirement
from portal.model_modules.equine_documents import HorseDocument
from portal.models import Team, UserProfile

User = get_user_model()


class EquineComplianceRequirementUITests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="ArenaLine Requirement UI")
        self.admin = User.objects.create_user(username="requirement-admin", password="test-pass-123")
        self.admin.profile.team = self.team
        self.admin.profile.role = UserProfile.Role.ADMIN
        self.admin.profile.save(update_fields=["team", "role"])
        self.client.force_login(self.admin)

    def test_manager_can_view_requirement_settings(self):
        response = self.client.get(reverse("horse_compliance_requirements"))
        self.assertContains(response, "Compliance Requirements")
        self.assertContains(response, "No requirements configured")
        self.assertContains(response, "Add requirement")

    def test_manager_can_add_document_requirement(self):
        response = self.client.post(reverse("horse_compliance_requirement_add"), {
            "name": "Registration papers",
            "requirement_type": HorseComplianceRequirement.RequirementType.DOCUMENT,
            "document_type": HorseDocument.DocumentType.REGISTRATION,
            "active": "on",
            "notes": "Required for active competition horses.",
        })
        self.assertRedirects(response, reverse("horse_compliance_requirements"))
        requirement = HorseComplianceRequirement.objects.get(team=self.team)
        self.assertEqual(requirement.document_type, HorseDocument.DocumentType.REGISTRATION)
        self.assertTrue(requirement.active)

    def test_manager_can_add_coggins_requirement(self):
        response = self.client.post(reverse("horse_compliance_requirement_add"), {
            "name": "Current Coggins",
            "requirement_type": HorseComplianceRequirement.RequirementType.COGGINS,
            "document_type": "",
            "active": "on",
            "notes": "",
        })
        self.assertRedirects(response, reverse("horse_compliance_requirements"))
        self.assertTrue(HorseComplianceRequirement.objects.filter(team=self.team, requirement_type="coggins").exists())

    def test_manager_can_edit_and_deactivate_requirement(self):
        requirement = HorseComplianceRequirement.objects.create(team=self.team, name="Insurance", requirement_type=HorseComplianceRequirement.RequirementType.DOCUMENT, document_type=HorseDocument.DocumentType.INSURANCE)
        response = self.client.post(reverse("horse_compliance_requirement_edit", args=[requirement.pk]), {
            "name": "Insurance",
            "requirement_type": HorseComplianceRequirement.RequirementType.DOCUMENT,
            "document_type": HorseDocument.DocumentType.INSURANCE,
            "notes": "Historical requirement",
        })
        self.assertRedirects(response, reverse("horse_compliance_requirements"))
        requirement.refresh_from_db()
        self.assertFalse(requirement.active)
        self.assertEqual(requirement.notes, "Historical requirement")

    def test_duplicate_requirement_name_is_rejected_case_insensitively(self):
        HorseComplianceRequirement.objects.create(team=self.team, name="Registration", requirement_type=HorseComplianceRequirement.RequirementType.DOCUMENT, document_type=HorseDocument.DocumentType.REGISTRATION)
        response = self.client.post(reverse("horse_compliance_requirement_add"), {
            "name": "registration",
            "requirement_type": HorseComplianceRequirement.RequirementType.DOCUMENT,
            "document_type": HorseDocument.DocumentType.REGISTRATION,
            "active": "on",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already exists")
        self.assertEqual(HorseComplianceRequirement.objects.filter(team=self.team).count(), 1)

    def test_non_manager_cannot_access_requirement_settings(self):
        rider = User.objects.create_user(username="requirement-rider", password="test-pass-123")
        rider.profile.team = self.team
        rider.profile.role = UserProfile.Role.RIDER
        rider.profile.save(update_fields=["team", "role"])
        self.client.force_login(rider)
        self.assertEqual(self.client.get(reverse("horse_compliance_requirements")).status_code, 403)
        self.assertEqual(self.client.get(reverse("horse_compliance_requirement_add")).status_code, 403)

    def test_cannot_edit_requirement_from_another_organization(self):
        other = Team.objects.create(name="Other Organization")
        requirement = HorseComplianceRequirement.objects.create(team=other, name="Other requirement", requirement_type=HorseComplianceRequirement.RequirementType.COGGINS)
        response = self.client.get(reverse("horse_compliance_requirement_edit", args=[requirement.pk]))
        self.assertEqual(response.status_code, 404)

    def test_registry_links_managers_to_requirement_settings(self):
        response = self.client.get(reverse("horse_list"))
        self.assertContains(response, "Compliance requirements")
        self.assertContains(response, reverse("horse_compliance_requirements"))
