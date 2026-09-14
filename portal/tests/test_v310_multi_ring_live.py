from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.public_site import PublicShowPublication
from portal.model_modules.show_day_state import ShowClassLiveState, ShowClassRingAssignment
from portal.models import Season, SeasonClass, Show, ShowClass, Team, UserProfile
from portal.publication import public_show_payload, public_show_schedule_payload


class MultiRingLiveTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
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
            name="Autumn Invitational",
            show_date=date(2026, 10, 10),
            status=Show.Status.ENTERED,
        )
        season_class_one = SeasonClass.objects.create(
            season=self.season,
            name="Futures Flat",
            team_level=SeasonClass.TeamLevel.FUTURES,
        )
        season_class_two = SeasonClass.objects.create(
            season=self.season,
            name="Upper Flat",
            team_level=SeasonClass.TeamLevel.UPPER,
        )
        self.class_one = ShowClass.objects.create(
            show=self.show,
            season_class=season_class_one,
            name="Futures Flat",
            class_number="H10",
            sort_order=1,
        )
        self.class_two = ShowClass.objects.create(
            show=self.show,
            season_class=season_class_two,
            name="Upper Flat",
            class_number="H2",
            sort_order=2,
        )
        ShowClassRingAssignment.objects.create(show_class=self.class_one, ring="Ring 1")
        ShowClassRingAssignment.objects.create(show_class=self.class_two, ring="Ring 2")
        self.publication = PublicShowPublication.objects.create(
            show=self.show,
            slug="autumn-invitational-rings",
            is_published=True,
            publish_schedule=True,
            publish_live_status=True,
        )
        self.admin = User.objects.create_user(username="ring-admin", password="testpass")
        self.admin.profile.team = self.team
        self.admin.profile.role = UserProfile.Role.ADMIN
        self.admin.profile.save(update_fields=["team", "role"])

    def start(self, show_class):
        self.client.force_login(self.admin)
        return self.client.post(
            reverse("show_class_live_status_update", args=[show_class.pk]),
            {"status": ShowClassLiveState.Status.IN_PROGRESS},
        )

    def test_different_rings_can_run_simultaneously(self):
        self.assertEqual(self.start(self.class_one).status_code, 302)
        self.assertEqual(self.start(self.class_two).status_code, 302)

        self.assertEqual(
            ShowClassLiveState.objects.get(show_class=self.class_one).status,
            ShowClassLiveState.Status.IN_PROGRESS,
        )
        self.assertEqual(
            ShowClassLiveState.objects.get(show_class=self.class_two).status,
            ShowClassLiveState.Status.IN_PROGRESS,
        )

        payload = public_show_payload(self.publication)
        active = payload["live_status"]["active_classes"]
        self.assertEqual(len(active), 2)
        self.assertEqual({item["ring"] for item in active}, {"Ring 1", "Ring 2"})
        self.assertEqual({item["state_label"] for item in active}, {"Now"})

        schedule = public_show_schedule_payload(self.publication)
        self.assertEqual({item["ring"] for item in schedule}, {"Ring 1", "Ring 2"})
        self.assertEqual([item["state"] for item in schedule], ["current", "current"])

    def test_same_ring_rejects_second_active_class(self):
        assignment = self.class_two.ring_assignment
        assignment.ring = "Ring 1"
        assignment.save(update_fields=["ring"])

        self.start(self.class_one)
        response = self.start(self.class_two)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ShowClassLiveState.objects.filter(show_class=self.class_two).exists())

    def test_ring_can_be_assigned_from_show_day_control(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("show_class_ring_update", args=[self.class_one.pk]),
            {"ring": "  Hunter   Ring  "},
        )
        self.assertEqual(response.status_code, 302)
        self.class_one.ring_assignment.refresh_from_db()
        self.assertEqual(self.class_one.ring_assignment.ring, "Hunter Ring")

    def test_blank_ring_uses_main_ring(self):
        self.class_one.ring_assignment.ring = ""
        self.class_one.ring_assignment.save(update_fields=["ring"])
        payload = public_show_schedule_payload(self.publication)
        self.assertEqual(payload[0]["ring"], "Main ring")
