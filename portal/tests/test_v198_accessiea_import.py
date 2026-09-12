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


class V198AccessIEAImportTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Test Team")
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

        self.rider = Rider.objects.create(
            team=self.team,
            first_name="Emma",
            last_name="Brown",
            iea_member_number="1234567",
        )
        self.flat = SeasonClass.objects.create(
            season=self.season,
            name="Varsity Open Equitation on the flat",
            team_level=SeasonClass.TeamLevel.UPPER,
            discipline="hunt_seat",
        )
        self.membership = SeasonMembership.objects.create(
            rider=self.rider,
            season=self.season,
            team_level=SeasonMembership.TeamLevel.UPPER,
        )
        self.membership.classes.add(self.flat)

    def upload(self, body):
        return SimpleUploadedFile(
            "Rider-Performance.csv",
            body.encode("utf-8"),
            content_type="text/csv",
        )

    def accessiea_csv(self, regular="5", region_team="4", region_individual="3", zone_individual=""):
        return (
            "#IEA,# of Shows,Rider Name,Class,Total Rider Points,"
            "9/7/2025 Blue Skies Riding Academy Show,"
            "2/7/2026 Zone 4 Region 3 Finals Team,"
            "2/7/2026 Zone 4 Region 3 Finals Individual,"
            "3/14/2026 Zone 4 Finals Individual\n"
            f"1234567,3,Emma Brown,Varsity Open Equitation on the flat,12,"
            f"{regular},{region_team},{region_individual},{zone_individual}\n"
        )

    def test_accessiea_preview_does_not_write(self):
        self.client.force_login(self.coach)
        response = self.client.post(
            reverse("season_history_import", args=[self.season.pk]),
            {"action": "preview", "csv_file": self.upload(self.accessiea_csv())},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Preview ready")
        self.assertContains(response, "Blue Skies Riding Academy Show")
        self.assertContains(response, "Zone 4 Region 3 Finals")
        self.assertEqual(Show.objects.count(), 0)

    def test_accessiea_commit_creates_regular_and_finals_tracks(self):
        self.client.force_login(self.coach)
        self.client.post(
            reverse("season_history_import", args=[self.season.pk]),
            {"action": "preview", "csv_file": self.upload(self.accessiea_csv())},
        )
        self.client.post(
            reverse("season_history_import", args=[self.season.pk]),
            {"action": "commit"},
        )

        self.assertEqual(ShowResult.objects.count(), 3)
        self.assertEqual(
            Show.objects.filter(
                name="Zone 4 Region 3 Finals",
                competition_level=Show.CompetitionLevel.REGIONAL,
            ).count(),
            1,
        )
        tracks = set(
            ShowEntry.objects.filter(
                show_class__show__competition_level=Show.CompetitionLevel.REGIONAL
            ).values_list("competition_track", flat=True)
        )
        self.assertEqual(
            tracks,
            {
                ShowEntry.CompetitionTrack.TEAM,
                ShowEntry.CompetitionTrack.INDIVIDUAL,
            },
        )

    def test_blank_cell_is_no_ride_but_zero_is_real_result(self):
        body = self.accessiea_csv(
            regular="0",
            region_team="",
            region_individual="",
            zone_individual="",
        )
        body = body.replace(",3,Emma Brown,", ",1,Emma Brown,").replace(",12,", ",0,")
        self.client.force_login(self.coach)
        self.client.post(
            reverse("season_history_import", args=[self.season.pk]),
            {"action": "preview", "csv_file": self.upload(body)},
        )
        self.client.post(
            reverse("season_history_import", args=[self.season.pk]),
            {"action": "commit"},
        )
        self.assertEqual(ShowResult.objects.count(), 1)
        result = ShowResult.objects.get()
        self.assertEqual(result.points, 0)
        self.assertTrue(result.manual_points)

    def test_iea_number_matches_even_when_name_differs(self):
        body = self.accessiea_csv().replace("Emma Brown", "Emma B. Brown")
        self.client.force_login(self.coach)
        response = self.client.post(
            reverse("season_history_import", args=[self.season.pk]),
            {"action": "preview", "csv_file": self.upload(body)},
        )
        self.assertContains(response, "matched by #IEA")
        self.assertNotContains(response, "was not found on this season roster")

    def test_mismatched_iea_does_not_fallback_to_exact_name(self):
        body = self.accessiea_csv().replace("1234567", "9999999")
        self.client.force_login(self.coach)
        response = self.client.post(
            reverse("season_history_import", args=[self.season.pk]),
            {"action": "preview", "csv_file": self.upload(body)},
        )
        self.assertContains(response, "Rider #9999999 (Emma Brown) was not found on this season roster")
        self.assertNotContains(response, "matched by exact name")

    def test_accessiea_header_variations_still_detect(self):
        body = self.accessiea_csv()
        body = body.replace(
            "#IEA,# of Shows,Rider Name,Class,Total Rider Points,",
            "#IEA, # OF SHOWS , rider name , CLASS , Total Rider Points ,",
            1,
        )
        self.client.force_login(self.coach)
        response = self.client.post(
            reverse("season_history_import", args=[self.season.pk]),
            {"action": "preview", "csv_file": self.upload(body)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Preview ready")
        self.assertNotContains(response, "Missing required column(s): rider_first_name")
