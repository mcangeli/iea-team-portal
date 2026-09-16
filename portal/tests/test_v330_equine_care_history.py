from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from portal.horse_models import Horse
from portal.model_modules.equine_care import HorseCareRecord
from portal.models import Team, UserProfile


User = get_user_model()


class EquineCareHistoryTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="ArenaLine Care History")
        self.admin = User.objects.create_user(username="care-history-admin", password="test-pass-123")
        self.admin.profile.team = self.team
        self.admin.profile.role = UserProfile.Role.ADMIN
        self.admin.profile.save(update_fields=["team", "role"])
        self.horse = Horse.objects.create(team=self.team, name="Atlas")
        self.client.force_login(self.admin)

    def _record(self, title, performed_date):
        return HorseCareRecord.objects.create(
            horse=self.horse,
            care_type=HorseCareRecord.CareType.FARRIER,
            title=title,
            performed_date=performed_date,
        )

    def test_full_history_groups_completed_care_by_year(self):
        self._record("2026 trim", date(2026, 8, 1))
        self._record("2025 trim", date(2025, 7, 1))
        response = self.client.get(reverse("horse_care_history", args=[self.horse.pk]))
        self.assertContains(response, "Completed care by year")
        self.assertContains(response, "2026 trim")
        self.assertContains(response, "2025 trim")
        self.assertContains(response, "2026")
        self.assertContains(response, "2025")

    def test_history_can_filter_to_one_year(self):
        self._record("Current year care", date(2026, 6, 1))
        self._record("Older care", date(2025, 6, 1))
        response = self.client.get(reverse("horse_care_history", args=[self.horse.pk]) + "?year=2025")
        self.assertContains(response, "Older care")
        self.assertNotContains(response, "Current year care")

    def test_horse_profile_links_to_full_history(self):
        response = self.client.get(reverse("horse_detail", args=[self.horse.pk]))
        self.assertContains(response, "View full history")
        self.assertContains(response, reverse("horse_care_history", args=[self.horse.pk]))

    def test_non_manager_cannot_view_care_history(self):
        rider = User.objects.create_user(username="care-history-rider", password="test-pass-123")
        rider.profile.team = self.team
        rider.profile.role = UserProfile.Role.RIDER
        rider.profile.save(update_fields=["team", "role"])
        self.client.force_login(rider)
        response = self.client.get(reverse("horse_care_history", args=[self.horse.pk]))
        self.assertEqual(response.status_code, 403)

    def test_cannot_view_another_organizations_horse_history(self):
        other_team = Team.objects.create(name="Other Barn")
        other_horse = Horse.objects.create(team=other_team, name="Comet")
        response = self.client.get(reverse("horse_care_history", args=[other_horse.pk]))
        self.assertEqual(response.status_code, 404)
