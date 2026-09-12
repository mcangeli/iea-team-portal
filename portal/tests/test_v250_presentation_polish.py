from datetime import date

from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.test import TestCase
from django.urls import reverse

from portal.host_show_models import HostShowFamilyPublication, HostShowOperations, ShowManagerAssignment
from portal.models import Season, Show, ShowLeadAssignment, Team, UserProfile


class V250PresentationPolishTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Presentation Polish Team")
        self.season = Season.objects.create(
            team=self.team,
            name="2026-2027",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 6, 30),
            is_active=True,
        )
        self.show = Show.objects.create(
            team=self.team,
            season=self.season,
            name="Polish Invitational",
            show_date=date(2026, 11, 28),
            financial_role=Show.FinancialRole.HOSTING_ATTENDING,
        )
        self.manager = self.make_user("polish-manager", UserProfile.Role.PARENT)
        self.lead = self.make_user("polish-lead", UserProfile.Role.PARENT)
        ShowManagerAssignment.objects.create(show=self.show, user=self.manager, active=True)
        ShowLeadAssignment.objects.create(show=self.show, user=self.lead, active=True)

    def make_user(self, username, role):
        user = User.objects.create_user(username=username, password="testpass")
        user.profile.team = self.team
        user.profile.role = role
        user.profile.save(update_fields=["team", "role"])
        return user

    def test_error_templates_initialize_saved_theme_and_offer_toggle(self):
        for template_name in ("403.html", "404.html", "500.html"):
            html = render_to_string(template_name)
            self.assertIn("iea-theme", html)
            self.assertIn('class="error-shell"', html)
            self.assertIn('id="theme-toggle"', html)
            self.assertIn("prefers-color-scheme: dark", html)

    def test_show_manager_dashboard_calls_out_unstarted_host_plan(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("dashboard_show_manager"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Host plan not started")
        self.assertContains(response, "No hosting budget entered")

    def test_show_lead_empty_command_center_explains_setup_state(self):
        self.assertFalse(HostShowOperations.objects.filter(show=self.show).exists())
        self.client.force_login(self.lead)
        response = self.client.get(reverse("host_command_center", args=[self.show.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Host plan not started")
        self.assertContains(response, "A Coach, Administrator, or Show Manager must start the host plan")
        self.assertFalse(HostShowOperations.objects.filter(show=self.show).exists())

    def test_published_family_page_explains_when_no_sections_are_selected(self):
        operations = HostShowOperations.objects.create(
            show=self.show,
            created_by=self.manager,
            updated_by=self.manager,
        )
        HostShowFamilyPublication.objects.create(
            operations=operations,
            published=True,
            updated_by=self.manager,
        )
        self.client.force_login(self.manager)
        response = self.client.get(reverse("host_family_information", args=[self.show.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Family information is published, but no sections are selected")
