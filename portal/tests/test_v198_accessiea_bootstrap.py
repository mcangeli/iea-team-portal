from datetime import date

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from portal.models import (
    Rider,
    Season,
    SeasonClass,
    SeasonMembership,
    Show,
    ShowEntry,
    ShowResult,
    Team,
    UserProfile,
)


class V198AccessIEABootstrapTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Test Team", discipline="hunt_seat")
        self.season = Season.objects.create(
            team=self.team,
            name="2025-26",
            start_date=date(2025, 8, 1),
            end_date=date(2026, 7, 31),
            is_active=False,
            is_closed=True,
        )
        self.coach = User.objects.create_user(username="coach", password="testpass")
        self.coach.profile.team = self.team
        self.coach.profile.role = UserProfile.Role.COACH
        self.coach.profile.save(update_fields=["team", "role"])

    def upload(self, rider_name="Karma Kilfoyle", iea="3358246",
               class_name="Varsity Open Equitation on the flat", points="5"):
        body = (
            "#IEA,# of Shows,Rider Name,Class,Total Rider Points,"
            "9/7/2025 Blue Skies Riding Academy Show\n"
            f"{iea},1,{rider_name},{class_name},{points},{points}\n"
        )
        return SimpleUploadedFile(
            "Rider-Performance.csv",
            body.encode("utf-8"),
            content_type="text/csv",
        )

    def preview(self, **kwargs):
        data = {
            "action": "preview",
            "bootstrap_missing": "on",
            "csv_file": self.upload(**kwargs),
        }
        return self.client.post(
            reverse("season_history_import", args=[self.season.pk]),
            data,
        )

    def test_preview_proposes_missing_rider_membership_class_and_assignment(self):
        self.client.force_login(self.coach)
        response = self.preview()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create rider Karma Kilfoyle")
        self.assertContains(response, "Season memberships")
        self.assertContains(response, "Season classes")
        self.assertEqual(Rider.objects.count(), 0)
        self.assertEqual(SeasonMembership.objects.count(), 0)
        self.assertEqual(SeasonClass.objects.count(), 0)
        self.assertEqual(ShowResult.objects.count(), 0)

    def test_commit_bootstraps_missing_records_then_imports_result(self):
        self.client.force_login(self.coach)
        self.preview()
        response = self.client.post(
            reverse("season_history_import", args=[self.season.pk]),
            {"action": "commit"},
        )
        self.assertRedirects(
            response, reverse("season_history_entry", args=[self.season.pk])
        )

        rider = Rider.objects.get()
        self.assertEqual(rider.iea_member_number, "3358246")
        membership = SeasonMembership.objects.get(rider=rider, season=self.season)
        self.assertEqual(membership.team_level, SeasonMembership.TeamLevel.UPPER)
        season_class = SeasonClass.objects.get()
        self.assertEqual(season_class.team_level, SeasonClass.TeamLevel.UPPER)
        self.assertTrue(membership.classes.filter(pk=season_class.pk).exists())
        self.assertEqual(Show.objects.count(), 1)
        self.assertEqual(ShowResult.objects.count(), 1)

    def test_existing_team_rider_gets_historical_membership_not_duplicate_rider(self):
        rider = Rider.objects.create(
            team=self.team,
            first_name="Karma",
            last_name="Kilfoyle",
            iea_member_number="3358246",
        )
        self.client.force_login(self.coach)
        response = self.preview()
        self.assertContains(response, "Add Karma Kilfoyle to 2025-26 as Upper School")
        self.assertNotContains(response, "Create rider Karma Kilfoyle")

        self.client.post(
            reverse("season_history_import", args=[self.season.pk]),
            {"action": "commit"},
        )
        self.assertEqual(Rider.objects.count(), 1)
        self.assertTrue(
            SeasonMembership.objects.filter(rider=rider, season=self.season).exists()
        )

    def test_existing_rider_without_iea_number_is_linked_by_exact_name(self):
        rider = Rider.objects.create(
            team=self.team,
            first_name="Karma",
            last_name="Kilfoyle",
            iea_member_number="",
        )
        self.client.force_login(self.coach)
        response = self.preview()
        self.assertContains(response, "#IEA will be added on commit")
        self.client.post(
            reverse("season_history_import", args=[self.season.pk]),
            {"action": "commit"},
        )
        rider.refresh_from_db()
        self.assertEqual(rider.iea_member_number, "3358246")
        self.assertEqual(Rider.objects.count(), 1)

    def test_unknown_team_level_blocks_bootstrap_instead_of_guessing(self):
        self.client.force_login(self.coach)
        response = self.preview(class_name="Open Equitation")
        self.assertContains(response, "Could not determine Futures vs Upper School")
        self.client.post(
            reverse("season_history_import", args=[self.season.pk]),
            {"action": "commit"},
            follow=True,
        )
        self.assertEqual(Rider.objects.count(), 0)
        self.assertEqual(ShowResult.objects.count(), 0)

    def test_future_class_bootstraps_as_futures(self):
        self.client.force_login(self.coach)
        self.preview(
            rider_name="Taylor Smith",
            iea="7777777",
            class_name="Future Intermediate Equitation on the flat",
        )
        self.client.post(
            reverse("season_history_import", args=[self.season.pk]),
            {"action": "commit"},
        )
        membership = SeasonMembership.objects.get()
        self.assertEqual(membership.team_level, SeasonMembership.TeamLevel.FUTURES)
        self.assertEqual(
            SeasonClass.objects.get().team_level,
            SeasonClass.TeamLevel.FUTURES,
        )
