from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.capabilities import OrganizationCapabilityAssignment
from portal.model_modules.finance import FinanceDomain
from portal.model_modules.people import Person
from portal.models import Team, UserProfile


class FinanceWorkspaceRenderTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Finance UI Barn")

    def _user(self, username, role=UserProfile.Role.PARENT):
        user = User.objects.create_user(username=username, password="pass12345")
        profile = user.profile
        profile.team = self.team
        profile.role = role
        profile.save(update_fields=["team", "role"])
        person = Person.objects.create(
            team=self.team,
            user=user,
            first_name=username,
            last_name="Tester",
        )
        return user, person

    def test_admin_finance_workspace_renders_and_links_payables(self):
        user, _ = self._user("finance-ui-admin", UserProfile.Role.ADMIN)
        self.client.force_login(user)

        response = self.client.get(reverse("finance_workspace"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "portal/finance_workspace_v350.html")
        self.assertContains(response, reverse("finance_payables"))

    def test_admin_payables_workspace_renders(self):
        user, _ = self._user("payables-ui-admin", UserProfile.Role.ADMIN)
        self.client.force_login(user)

        response = self.client.get(reverse("finance_payables"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "portal/finance_payables_v370.html")
        self.assertEqual(response.context["selected_domain"], FinanceDomain.GENERAL)
        self.assertContains(response, "Payables")

    def test_iea_only_finance_user_renders_iea_payables(self):
        user, person = self._user("payables-ui-iea")
        OrganizationCapabilityAssignment.objects.create(
            team=self.team,
            person=person,
            capability=OrganizationCapabilityAssignment.Capability.MANAGE_IEA_FINANCE,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("finance_payables"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_domain"], FinanceDomain.IEA)
        self.assertNotContains(response, "domain=general")

    def test_unprivileged_user_cannot_open_finance_workspaces(self):
        user, _ = self._user("finance-ui-parent")
        self.client.force_login(user)

        self.assertEqual(self.client.get(reverse("finance_workspace")).status_code, 403)
        self.assertEqual(self.client.get(reverse("finance_payables")).status_code, 403)
