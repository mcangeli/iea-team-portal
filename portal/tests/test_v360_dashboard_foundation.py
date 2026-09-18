from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.models import ShowAvailability, Team, UserProfile


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

    def test_dashboard_keeps_iea_competition_as_an_area_when_season_exists(self):
        from datetime import date
        from portal.models import Season
        Season.objects.create(team=self.team, name="2026-2027", start_date=date(2026, 8, 1), end_date=date(2027, 7, 31), is_active=True)
        response = self.client.get(reverse("dashboard_general"))
        keys = {area["key"] for area in response.context["operational_areas"]}
        self.assertIn("competition", keys)
