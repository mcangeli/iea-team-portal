from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from portal.horse_models import Horse, HorseCogginsRecord, HorseSeasonProfile
from portal.models import Season, SeasonClass, Team, UserProfile


class HorseRegistryTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Test Team", short_name="Test")
        self.other_team = Team.objects.create(name="Other Team", short_name="Other")
        today = timezone.localdate()
        self.season = Season.objects.create(
            team=self.team,
            name="2026-2027",
            start_date=today,
            end_date=today + timedelta(days=250),
            is_active=True,
        )
        self.season_class = SeasonClass.objects.create(
            season=self.season,
            name="Open Flat",
            team_level=SeasonClass.TeamLevel.UPPER,
            sort_order=1,
        )
        self.admin = User.objects.create_user("horseadmin", password="testpass123")
        UserProfile.objects.create(user=self.admin, team=self.team, role=UserProfile.Role.ADMIN)
        self.rider = User.objects.create_user("horserider", password="testpass123")
        UserProfile.objects.create(user=self.rider, team=self.team, role=UserProfile.Role.RIDER)
        self.horse = Horse.objects.create(team=self.team, name="Biscuit", breed="Quarter Horse Cross")

    def test_coggins_statuses(self):
        today = timezone.localdate()
        current = HorseCogginsRecord.objects.create(
            horse=self.horse,
            test_date=today - timedelta(days=30),
            expiration_date=today + timedelta(days=60),
        )
        expiring = HorseCogginsRecord.objects.create(
            horse=self.horse,
            test_date=today - timedelta(days=300),
            expiration_date=today + timedelta(days=15),
        )
        expired = HorseCogginsRecord.objects.create(
            horse=self.horse,
            test_date=today - timedelta(days=400),
            expiration_date=today - timedelta(days=1),
        )
        self.assertEqual(current.status, "current")
        self.assertEqual(expiring.status, "expiring")
        self.assertEqual(expired.status, "expired")

    def test_season_profile_links_existing_season_classes(self):
        profile = HorseSeasonProfile.objects.create(horse=self.horse, season=self.season)
        profile.eligible_classes.add(self.season_class)
        self.assertEqual(list(profile.eligible_classes.all()), [self.season_class])

    def test_team_member_can_view_active_horse(self):
        self.client.login(username="horserider", password="testpass123")
        response = self.client.get(reverse("horse_detail", args=[self.horse.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Biscuit")

    def test_rider_cannot_create_horse(self):
        self.client.login(username="horserider", password="testpass123")
        response = self.client.get(reverse("horse_create"))
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_horse(self):
        self.client.login(username="horseadmin", password="testpass123")
        response = self.client.post(reverse("horse_create"), {
            "name": "Scout",
            "crop_preference": "optional",
            "spur_preference": "no",
            "lead_change": "simple",
            "ownership_type": "private",
            "active": "on",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Horse.objects.filter(team=self.team, name="Scout").exists())

    def test_horse_detail_is_team_scoped(self):
        other = Horse.objects.create(team=self.other_team, name="Not Ours")
        self.client.login(username="horseadmin", password="testpass123")
        response = self.client.get(reverse("horse_detail", args=[other.pk]))
        self.assertEqual(response.status_code, 404)

    def test_inactive_horse_hidden_from_rider(self):
        self.horse.active = False
        self.horse.save(update_fields=["active"])
        self.client.login(username="horserider", password="testpass123")
        detail = self.client.get(reverse("horse_detail", args=[self.horse.pk]))
        listing = self.client.get(reverse("horse_list"))
        self.assertEqual(detail.status_code, 403)
        self.assertNotContains(listing, "Biscuit")
