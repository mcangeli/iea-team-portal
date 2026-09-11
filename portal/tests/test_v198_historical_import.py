from datetime import date
from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from portal.models import (
    AuditEvent,
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


HEADERS = (
    "rider_first_name,rider_last_name,show_name,show_date,competition_level,"
    "class_name,competition_track,place,points,horse_name,venue,notes,"
    "futures_team_place,upper_team_place\n"
)


class V198HistoricalImportTests(TestCase):
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
        self.coach = User.objects.create_user(
            username="coach", password="testpass"
        )
        self.coach.profile.team = self.team
        self.coach.profile.role = UserProfile.Role.COACH
        self.coach.profile.save(update_fields=["team", "role"])

        self.rider = Rider.objects.create(
            team=self.team,
            first_name="Emma",
            last_name="Brown",
            preferred_name="Em",
            grade=8,
        )
        self.season_class = SeasonClass.objects.create(
            season=self.season,
            name="Intermediate Flat",
            team_level=SeasonClass.TeamLevel.FUTURES,
            discipline="hunt_seat",
            sort_order=10,
        )
        self.membership = SeasonMembership.objects.create(
            rider=self.rider,
            season=self.season,
            team_level=SeasonMembership.TeamLevel.FUTURES,
        )
        self.membership.classes.add(self.season_class)

    def csv_upload(self, rows):
        content = HEADERS + "\n".join(rows) + "\n"
        return SimpleUploadedFile(
            "history.csv",
            content.encode("utf-8"),
            content_type="text/csv",
        )

    def preview(self, rows):
        return self.client.post(
            reverse("season_history_import", args=[self.season.pk]),
            {"action": "preview", "csv_file": self.csv_upload(rows)},
        )

    def test_valid_csv_previews_without_writing_database(self):
        self.client.force_login(self.coach)
        response = self.preview([
            "Emma,Brown,Fall Show,2025-10-12,regular,Intermediate Flat,,2,,Horse A,Venue A,source note,,"
        ])
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Preview ready")
        self.assertContains(response, "Ready")
        self.assertEqual(Show.objects.count(), 0)
        self.assertEqual(ShowResult.objects.count(), 0)

    def test_commit_creates_historical_show_entry_and_result(self):
        self.client.force_login(self.coach)
        self.preview([
            "Emma,Brown,Fall Show,2025-10-12,regular,Intermediate Flat,,2,,Horse A,Venue A,source note,,"
        ])
        response = self.client.post(
            reverse("season_history_import", args=[self.season.pk]),
            {"action": "commit"},
        )
        self.assertRedirects(
            response, reverse("season_history_entry", args=[self.season.pk])
        )

        show = Show.objects.get()
        self.assertTrue(show.is_historical_import)
        self.assertEqual(show.status, Show.Status.COMPLETE)
        result = ShowResult.objects.get()
        self.assertEqual(result.entry.rider, self.rider)
        self.assertEqual(result.entry.competition_track, ShowEntry.CompetitionTrack.REGULAR)
        self.assertEqual(result.place, 2)
        self.assertEqual(result.horse_name, "Horse A")
        self.assertTrue(
            AuditEvent.objects.filter(
                season=self.season,
                summary__icontains="Historical CSV import",
            ).exists()
        )

    def test_matching_existing_result_is_previewed_as_duplicate_and_skipped(self):
        show = Show.objects.create(
            team=self.team,
            season=self.season,
            name="Fall Show",
            show_date=date(2025, 10, 12),
            competition_level=Show.CompetitionLevel.REGULAR,
            status=Show.Status.COMPLETE,
        )
        show_class = show.classes.create(
            season_class=self.season_class,
            name=self.season_class.name,
            discipline=self.season_class.discipline,
        )
        entry = ShowEntry.objects.create(
            show_class=show_class,
            rider=self.rider,
            competition_track=ShowEntry.CompetitionTrack.REGULAR,
            status=ShowEntry.Status.ENTERED,
        )
        ShowResult.objects.create(entry=entry, place=2)

        self.client.force_login(self.coach)
        response = self.preview([
            "Emma,Brown,Fall Show,2025-10-12,regular,Intermediate Flat,,2,,Horse A,Venue A,,,"
        ])
        self.assertContains(response, "Duplicate")
        self.client.post(
            reverse("season_history_import", args=[self.season.pk]),
            {"action": "commit"},
        )
        self.assertEqual(ShowResult.objects.count(), 1)

    def test_unmatched_rider_blocks_commit(self):
        self.client.force_login(self.coach)
        response = self.preview([
            "Unknown,Rider,Fall Show,2025-10-12,regular,Intermediate Flat,,2,,Horse A,Venue A,,,"
        ])
        self.assertContains(response, "Rider was not found on this season roster.")
        response = self.client.post(
            reverse("season_history_import", args=[self.season.pk]),
            {"action": "commit"},
            follow=True,
        )
        self.assertContains(response, "Fix the validation errors")
        self.assertEqual(ShowResult.objects.count(), 0)

    def test_preferred_name_can_match_rider(self):
        self.client.force_login(self.coach)
        response = self.preview([
            "Em,Brown,Fall Show,2025-10-12,regular,Intermediate Flat,,2,,,,,,"
        ])
        self.assertContains(response, "Preview ready")
        self.assertNotContains(response, "Rider was not found")

    def test_finals_row_requires_track(self):
        self.client.force_login(self.coach)
        response = self.preview([
            "Emma,Brown,Region Finals,2026-02-01,regional,Intermediate Flat,,2,,,,,,"
        ])
        self.assertContains(
            response,
            "Finals rows require competition_track of individual or team.",
        )

    def test_archived_season_import_is_allowed(self):
        self.assertTrue(self.season.is_closed)
        self.client.force_login(self.coach)
        self.preview([
            "Emma,Brown,Fall Show,2025-10-12,regular,Intermediate Flat,,2,,,,,,"
        ])
        self.client.post(
            reverse("season_history_import", args=[self.season.pk]),
            {"action": "commit"},
        )
        self.assertEqual(ShowResult.objects.count(), 1)
        self.season.refresh_from_db()
        self.assertTrue(self.season.is_closed)

    def test_template_download_uses_season_rider_and_class(self):
        self.client.force_login(self.coach)
        response = self.client.get(
            reverse("season_history_import_template", args=[self.season.pk])
        )
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("rider_first_name", content)
        self.assertIn("Emma", content)
        self.assertIn("Intermediate Flat", content)
