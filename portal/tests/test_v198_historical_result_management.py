from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.models import (
    AuditEvent,
    Rider,
    Season,
    SeasonClass,
    SeasonMembership,
    Show,
    ShowClass,
    ShowEntry,
    ShowResult,
    Team,
    UserProfile,
)


class V198HistoricalResultManagementTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Test Team")
        self.season = Season.objects.create(
            team=self.team,
            name="2025-26",
            start_date=date(2025, 8, 1),
            end_date=date(2026, 7, 31),
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
        )
        self.other_rider = Rider.objects.create(
            team=self.team,
            first_name="Ava",
            last_name="Smith",
        )
        self.flat = SeasonClass.objects.create(
            season=self.season,
            name="Varsity Open Equitation on the flat",
            team_level=SeasonClass.TeamLevel.UPPER,
        )
        self.fences = SeasonClass.objects.create(
            season=self.season,
            name="Varsity Open Equitation o/f 2'6\"",
            team_level=SeasonClass.TeamLevel.UPPER,
        )
        for rider in [self.rider, self.other_rider]:
            membership = SeasonMembership.objects.create(
                rider=rider,
                season=self.season,
                team_level=SeasonMembership.TeamLevel.UPPER,
            )
            membership.classes.add(self.flat, self.fences)

        self.show = Show.objects.create(
            team=self.team,
            season=self.season,
            name="Historical Show",
            show_date=date(2025, 10, 1),
            status=Show.Status.COMPLETE,
            is_historical_import=True,
        )
        self.show_class = ShowClass.objects.create(
            show=self.show,
            season_class=self.flat,
            name=self.flat.name,
        )
        self.entry = ShowEntry.objects.create(
            show_class=self.show_class,
            rider=self.rider,
            competition_track=ShowEntry.CompetitionTrack.REGULAR,
            status=ShowEntry.Status.ENTERED,
        )
        self.result = ShowResult.objects.create(
            entry=self.entry,
            place=2,
            points=Decimal("5.0"),
            manual_points=True,
        )

    def test_rider_history_shows_edit_delete_for_historical_result(self):
        self.client.force_login(self.coach)
        response = self.client.get(reverse("rider_history", args=[self.rider.pk]))
        self.assertContains(response, reverse("historical_result_edit", args=[self.result.pk]))
        self.assertContains(response, reverse("historical_result_delete", args=[self.result.pk]))

    def test_edit_historical_result_on_archived_season(self):
        self.client.force_login(self.coach)
        response = self.client.post(
            reverse("historical_result_edit", args=[self.result.pk]),
            {
                "season_class": self.fences.pk,
                "competition_track": ShowEntry.CompetitionTrack.REGULAR,
                "place": 1,
                "manual_points": "on",
                "points": "7.0",
                "horse_name": "Horse A",
                "notes": "Corrected from source",
            },
        )
        self.assertRedirects(response, reverse("rider_history", args=[self.rider.pk]))
        self.result.refresh_from_db()
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.show_class.season_class, self.fences)
        self.assertEqual(self.result.place, 1)
        self.assertEqual(self.result.points, Decimal("7.0"))
        self.assertEqual(self.result.horse_name, "Horse A")
        self.assertTrue(
            AuditEvent.objects.filter(
                season=self.season,
                summary__icontains="Edited historical result",
            ).exists()
        )

    def test_delete_only_one_riders_result_preserves_shared_show(self):
        other_entry = ShowEntry.objects.create(
            show_class=self.show_class,
            rider=self.other_rider,
            competition_track=ShowEntry.CompetitionTrack.REGULAR,
            status=ShowEntry.Status.ENTERED,
        )
        ShowResult.objects.create(
            entry=other_entry,
            place=3,
            points=Decimal("4.0"),
            manual_points=True,
        )

        self.client.force_login(self.coach)
        response = self.client.post(
            reverse("historical_result_delete", args=[self.result.pk])
        )
        self.assertRedirects(response, reverse("rider_history", args=[self.rider.pk]))
        self.assertFalse(ShowResult.objects.filter(pk=self.result.pk).exists())
        self.assertTrue(Show.objects.filter(pk=self.show.pk).exists())
        self.assertTrue(ShowResult.objects.filter(entry=other_entry).exists())

    def test_delete_last_result_cleans_up_empty_imported_show(self):
        self.client.force_login(self.coach)
        self.client.post(reverse("historical_result_delete", args=[self.result.pk]))
        self.assertFalse(Show.objects.filter(pk=self.show.pk).exists())
        self.assertTrue(
            AuditEvent.objects.filter(
                season=self.season,
                summary__icontains="Deleted historical result",
            ).exists()
        )

    def test_non_historical_live_result_cannot_use_historical_editor(self):
        live_show = Show.objects.create(
            team=self.team,
            season=self.season,
            name="Normal Show",
            show_date=date(2025, 11, 1),
            status=Show.Status.COMPLETE,
            is_historical_import=False,
        )
        live_class = ShowClass.objects.create(
            show=live_show,
            season_class=self.flat,
            name=self.flat.name,
        )
        live_entry = ShowEntry.objects.create(
            show_class=live_class,
            rider=self.rider,
            competition_track=ShowEntry.CompetitionTrack.REGULAR,
            status=ShowEntry.Status.ENTERED,
        )
        live_result = ShowResult.objects.create(
            entry=live_entry,
            place=2,
        )
        self.client.force_login(self.coach)
        response = self.client.get(
            reverse("historical_result_edit", args=[live_result.pk])
        )
        self.assertEqual(response.status_code, 403)
