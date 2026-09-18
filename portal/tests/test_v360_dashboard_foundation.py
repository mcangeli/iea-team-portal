from django.contrib.auth.models import User
from django.test import Client
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from portal.models import ShowAvailability, Team, UserProfile
from portal.model_modules.lessons import LessonProgram, LessonSeries, LessonOccurrence, LessonAssignment
from portal.model_modules.people import Person


class V360DashboardFoundationTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
        self.user = User.objects.create_user(username="dashboard-admin", password="pass12345")
        self.user.profile.team = self.team
        self.user.profile.role = UserProfile.Role.ADMIN
        self.user.profile.save(update_fields=["team", "role"])
        self.client.force_login(self.user)

    def test_dashboard_get_does_not_create_show_availability(self):
        before = ShowAvailability.objects.count()
        self.client.get(reverse("dashboard_general"))
        self.assertEqual(ShowAvailability.objects.count(), before)

    def test_dashboard_exposes_arenaline_operational_areas(self):
        response = self.client.get(reverse("dashboard_general"))
        self.assertEqual(response.status_code, 200)
        keys = {area["key"] for area in response.context["operational_areas"]}
        self.assertIn("calendar", keys)
        self.assertIn("people", keys)
        self.assertIn("horses", keys)
        self.assertIn("finance", keys)

    def test_general_barn_dashboard_keeps_iea_competition_out_when_season_exists(self):
        from datetime import date
        from portal.models import Season
        Season.objects.create(team=self.team, name="2026-2027", start_date=date(2026, 8, 1), end_date=date(2027, 7, 31), is_active=True)
        response = self.client.get(reverse("dashboard"))
        keys = {area["key"] for area in response.context["operational_areas"]}
        snapshot_keys = {snapshot["key"] for snapshot in response.context["domain_snapshots"]}
        self.assertNotIn("competition", keys)
        self.assertNotIn("competition", snapshot_keys)

    def test_admin_quick_actions_cover_daily_operations(self):
        response = self.client.get(reverse("dashboard_general"))
        keys = {action["key"] for action in response.context["quick_actions"]}
        self.assertIn("calendar", keys)
        self.assertIn("actions", keys)
        self.assertIn("people", keys)
        self.assertIn("lessons", keys)
        self.assertIn("horses", keys)
        self.assertIn("finance", keys)

    def test_dashboard_renders_quick_action_command_bar(self):
        response = self.client.get(reverse("dashboard_general"))
        self.assertContains(response, "Move the day forward")
        self.assertContains(response, "Open calendar")
        self.assertContains(response, "Action items")

    def test_dashboard_exposes_cockpit_collections(self):
        response = self.client.get(reverse("dashboard_general"))
        self.assertIn("schedule_items", response.context)
        self.assertIn("attention_items", response.context)

    def test_empty_dashboard_has_useful_cockpit_states(self):
        response = self.client.get(reverse("dashboard_general"))
        self.assertContains(response, "The in gate is open.")
        self.assertContains(response, "Nothing is calling for attention.")

    def test_admin_dashboard_exposes_permission_aware_domain_snapshots(self):
        response = self.client.get(reverse("dashboard_general"))
        keys = {snapshot["key"] for snapshot in response.context["domain_snapshots"]}
        self.assertIn("horses", keys)
        self.assertIn("lessons", keys)
        self.assertIn("finance", keys)

    def test_dashboard_renders_operations_pulse(self):
        response = self.client.get(reverse("dashboard_general"))
        self.assertContains(response, "OPERATIONS PULSE", html=False)
        self.assertContains(response, "Across the barn")

    def test_admin_can_open_every_role_dashboard(self):
        response = self.client.get(reverse("my_team"))
        urls = {link["url"] for link in response.context["team_workspace_links"]}
        expected = {
            reverse("my_team"),
            reverse("dashboard_coach"),
            reverse("dashboard_team_parent"),
            reverse("dashboard_secretary"),
            reverse("dashboard_show_lead"),
            reverse("dashboard_show_manager"),
        }
        self.assertEqual(urls, expected)
        for url in expected:
            self.assertEqual(self.client.get(url).status_code, 200)

    def test_iea_role_workspaces_stay_anchored_to_my_team_and_show_announcements(self):
        response = self.client.get(reverse("dashboard_coach"))
        self.assertEqual(response.status_code, 200)
        urls = {link["url"] for link in response.context["workspace_links"]}
        self.assertIn(reverse("my_team"), urls)
        self.assertNotIn(reverse("dashboard_general"), urls)
        self.assertContains(response, "TEAM NOTES")
        self.assertContains(response, "Announcements")

    def test_non_admin_dashboard_does_not_inherit_admin_workspace_switcher(self):
        rider_user = User.objects.create_user(username="dashboard-rider", password="pass12345")
        rider_user.profile.team = self.team
        rider_user.profile.role = UserProfile.Role.RIDER
        rider_user.profile.save(update_fields=["team", "role"])
        rider_client = Client()
        rider_client.force_login(rider_user)
        response = rider_client.get(reverse("dashboard_general"))
        urls = {link["url"] for link in response.context["workspace_links"]}
        self.assertNotIn(reverse("dashboard_coach"), urls)
        self.assertNotIn(reverse("dashboard_secretary"), urls)
        self.assertNotIn(reverse("dashboard_show_lead"), urls)
        self.assertNotIn(reverse("dashboard_show_manager"), urls)

    def test_non_admin_dashboard_does_not_expose_admin_operational_domains(self):
        rider_user = User.objects.create_user(username="dashboard-rider-domains", password="pass12345")
        rider_user.profile.team = self.team
        rider_user.profile.role = UserProfile.Role.RIDER
        rider_user.profile.save(update_fields=["team", "role"])
        rider_client = Client()
        rider_client.force_login(rider_user)
        response = rider_client.get(reverse("dashboard_general"))
        area_keys = {area["key"] for area in response.context["operational_areas"]}
        snapshot_keys = {snapshot["key"] for snapshot in response.context["domain_snapshots"]}
        self.assertNotIn("horses", area_keys)
        self.assertNotIn("finance", area_keys)
        self.assertNotIn("horses", snapshot_keys)
        self.assertNotIn("finance", snapshot_keys)


    def test_admin_root_dashboard_matches_team_overview_context(self):
        root = self.client.get(reverse("dashboard"))
        overview = self.client.get(reverse("dashboard_general"))
        self.assertEqual(root.status_code, 200)
        self.assertEqual(root.resolver_match.func, __import__("portal.views", fromlist=["dashboard"]).dashboard)
        self.assertTemplateUsed(root, "portal/dashboard.html")
        for key in ("quick_actions", "operational_areas", "domain_snapshots"):
            self.assertEqual(root.context[key], overview.context[key])
        self.assertEqual(root.context["workspace_links"], [])
        self.assertEqual(root.context["can_manage_horses"], overview.context["can_manage_horses"])
        self.assertEqual(root.context["active_horse_count"], overview.context["active_horse_count"])


    def test_general_barn_dashboard_does_not_render_iea_workspace_switcher(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.context["workspace_links"], [])
        self.assertNotContains(response, 'aria-label="Role workspaces"')

    def test_iea_team_hub_exposes_admin_team_workspaces(self):
        response = self.client.get(reverse("my_team"))
        self.assertEqual(response.status_code, 200)
        urls = {link["url"] for link in response.context["team_workspace_links"]}
        self.assertIn(reverse("dashboard_coach"), urls)
        self.assertIn(reverse("dashboard_team_parent"), urls)
        self.assertIn(reverse("dashboard_secretary"), urls)
        self.assertIn(reverse("dashboard_show_lead"), urls)
        self.assertIn(reverse("dashboard_show_manager"), urls)


    def test_rider_root_dashboard_is_general_barn_safe(self):
        rider_user = User.objects.create_user(username="dashboard-rider-root", password="pass12345")
        rider_user.profile.team = self.team
        rider_user.profile.role = UserProfile.Role.RIDER
        rider_user.profile.save(update_fields=["team", "role"])
        rider_client = Client()
        rider_client.force_login(rider_user)
        response = rider_client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "portal/dashboard.html")
        self.assertNotIn("competition", {area["key"] for area in response.context["operational_areas"]})
        self.assertNotIn("competition", {snapshot["key"] for snapshot in response.context["domain_snapshots"]})


    def test_real_person_rider_dashboard_filters_lesson_occurrences_without_500(self):
        rider_user = User.objects.create_user(username="dashboard-real-person-rider", password="pass12345")
        rider_user.profile.team = self.team
        rider_user.profile.role = UserProfile.Role.RIDER
        rider_user.profile.save(update_fields=["team", "role"])
        person = Person.objects.create(team=self.team, user=rider_user, first_name="Real", last_name="Rider")
        program = LessonProgram.objects.create(team=self.team, name="Barn Lessons")
        series = LessonSeries.objects.create(program=program, name="Thursday Lessons")
        occurrence = LessonOccurrence.objects.create(
            series=series,
            title="Thursday Lesson",
            starts_at=timezone.now() + timedelta(days=1),
        )
        LessonAssignment.objects.create(
            occurrence=occurrence,
            person=person,
            role=LessonAssignment.Role.PARTICIPANT,
        )
        rider_client = Client()
        rider_client.force_login(rider_user)
        response = rider_client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Thursday Lesson")
