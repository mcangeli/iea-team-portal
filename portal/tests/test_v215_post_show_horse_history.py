from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from portal.horse_models import Horse, HorseShowAssignment
from portal.models import Season, SeasonClass, Show, ShowClass, Team, UserProfile
from portal.post_show_horse_models import ShowHorseHistoryRecord
from portal.post_show_horse_service import build_post_show_horse_history, finalize_post_show_horse_history
from portal.show_readiness_models import ShowLeasedHorse


class V215PostShowHorseHistoryTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="History Team")
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
            name="Fall Show",
            show_date=date(2026, 10, 10),
            status=Show.Status.COMPLETE,
        )
        self.season_class = SeasonClass.objects.create(
            season=self.season,
            name="Intermediate Flat",
            team_level=SeasonClass.TeamLevel.UPPER,
        )
        self.show_class = ShowClass.objects.create(
            show=self.show,
            season_class=self.season_class,
            name=self.season_class.name,
        )
        self.coach = User.objects.create_user(username="coach215", password="testpass")
        self.coach.profile.team = self.team
        self.coach.profile.role = UserProfile.Role.COACH
        self.coach.profile.save(update_fields=["team", "role"])

        self.registry_horse = Horse.objects.create(team=self.team, name="Atlas")
        self.assignment = HorseShowAssignment.objects.create(
            horse=self.registry_horse,
            show=self.show,
            available=True,
        )
        self.assignment.show_classes.add(self.show_class)

        self.leased = ShowLeasedHorse.objects.create(
            show=self.show,
            barn_name="Lease One",
            provider="Host Barn",
            available=True,
        )
        self.leased.show_classes.add(self.show_class)

    def test_generate_snapshot_captures_registry_and_leased_horses(self):
        history = build_post_show_horse_history(self.show, self.coach)
        self.assertEqual(history.records.count(), 2)
        registry = history.records.get(source_type=ShowHorseHistoryRecord.SourceType.REGISTRY)
        leased = history.records.get(source_type=ShowHorseHistoryRecord.SourceType.LEASED)
        self.assertEqual(registry.horse, self.registry_horse)
        self.assertEqual(registry.class_snapshot[0]["name"], "Intermediate Flat")
        self.assertIsNone(leased.horse)
        self.assertEqual(leased.provider, "Host Barn")

    def test_leased_placeholder_can_reconcile_to_registry_horse(self):
        history = build_post_show_horse_history(self.show, self.coach)
        actual_horse = Horse.objects.create(team=self.team, name="Comet")
        leased = history.records.get(source_type=ShowHorseHistoryRecord.SourceType.LEASED)
        leased.horse = actual_horse
        leased.save()
        self.assertTrue(leased.reconciled_from_leased)
        self.assertEqual(actual_horse.show_history_records.get(), leased)

    def test_final_history_cannot_be_rebuilt(self):
        history = build_post_show_horse_history(self.show, self.coach)
        finalized = finalize_post_show_horse_history(history, self.coach)
        self.assertTrue(finalized.is_final)
        self.assertIsNotNone(finalized.finalized_at)
        with self.assertRaises(ValidationError):
            build_post_show_horse_history(self.show, self.coach)

    def test_workspace_is_manager_only(self):
        self.client.force_login(self.coach)
        response = self.client.post(
            reverse("post_show_horse_history", args=[self.show.pk]),
            {"action": "generate"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(hasattr(self.show, "horse_history") or self.show.__class__.objects.get(pk=self.show.pk).horse_history)

        parent = User.objects.create_user(username="parent215", password="testpass")
        parent.profile.team = self.team
        parent.profile.role = UserProfile.Role.PARENT
        parent.profile.save(update_fields=["team", "role"])
        self.client.force_login(parent)
        self.assertEqual(
            self.client.get(reverse("post_show_horse_history", args=[self.show.pk])).status_code,
            403,
        )
