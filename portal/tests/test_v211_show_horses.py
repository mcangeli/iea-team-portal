from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from portal.horse_models import Horse, HorseShowAssignment, HorseShowAward
from portal.models import Season, SeasonClass, Show, ShowClass, Team, UserProfile


class ShowHorseAssignmentTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Test Team", short_name="Test")
        today = timezone.localdate()
        self.season = Season.objects.create(
            team=self.team, name="2026-2027", start_date=today,
            end_date=today + timedelta(days=250), is_active=True,
        )
        self.season_class = SeasonClass.objects.create(
            season=self.season, name="Open Flat",
            team_level=SeasonClass.TeamLevel.UPPER, sort_order=1,
        )
        self.show = Show.objects.create(
            team=self.team, season=self.season, name="Fall Show", show_date=today + timedelta(days=10),
        )
        self.show_class = ShowClass.objects.create(
            show=self.show, season_class=self.season_class, name="Open Flat", sort_order=1,
        )
        self.horse = Horse.objects.create(
            team=self.team, name="Biscuit", sex=Horse.Sex.GELDING,
            crop_preference=Horse.Preference.OPTIONAL,
            spur_preference=Horse.Preference.NO,
            lead_change=Horse.LeadChange.FLYING,
        )
        self.admin = User.objects.create_user("horseadmin211", password="testpass123")
        self.admin.profile.team = self.team
        self.admin.profile.role = UserProfile.Role.ADMIN
        self.admin.profile.save(update_fields=["team", "role"])
        self.rider = User.objects.create_user("horserider211", password="testpass123")
        self.rider.profile.team = self.team
        self.rider.profile.role = UserProfile.Role.RIDER
        self.rider.profile.save(update_fields=["team", "role"])

    def test_assignment_links_registry_horse_to_show_and_classes(self):
        assignment = HorseShowAssignment.objects.create(show=self.show, horse=self.horse)
        assignment.show_classes.add(self.show_class)
        self.assertEqual(assignment.show, self.show)
        self.assertEqual(list(assignment.show_classes.all()), [self.show_class])
        self.assertEqual(assignment.effective_crop_preference, Horse.Preference.OPTIONAL)

    def test_show_override_wins_over_registry_default(self):
        assignment = HorseShowAssignment.objects.create(
            show=self.show, horse=self.horse, crop_preference=Horse.Preference.NO,
            lead_change=Horse.LeadChange.SIMPLE,
        )
        self.assertEqual(assignment.effective_crop_preference, Horse.Preference.NO)
        self.assertEqual(assignment.effective_lead_change, Horse.LeadChange.SIMPLE)
        self.assertEqual(assignment.effective_spur_preference, Horse.Preference.NO)

    def test_admin_can_add_horse_to_show(self):
        self.client.login(username="horseadmin211", password="testpass123")
        response = self.client.post(reverse("show_horse_add", args=[self.show.pk]), {
            "horse": self.horse.pk,
            "available": "on",
            "show_classes": [self.show_class.pk],
            "crop_preference": "",
            "spur_preference": "",
            "lead_change": "",
            "notes": "Good draw horse",
        })
        self.assertEqual(response.status_code, 302)
        assignment = HorseShowAssignment.objects.get(show=self.show, horse=self.horse)
        self.assertEqual(list(assignment.show_classes.all()), [self.show_class])

    def test_rider_can_view_but_cannot_manage_show_horses(self):
        HorseShowAssignment.objects.create(show=self.show, horse=self.horse)
        self.client.login(username="horserider211", password="testpass123")
        listing = self.client.get(reverse("show_horses", args=[self.show.pk]))
        add = self.client.get(reverse("show_horse_add", args=[self.show.pk]))
        self.assertEqual(listing.status_code, 200)
        self.assertContains(listing, "Biscuit")
        self.assertEqual(add.status_code, 403)

    def test_horse_of_day_tracks_morning_and_afternoon_separately(self):
        assignment = HorseShowAssignment.objects.create(show=self.show, horse=self.horse)
        morning = HorseShowAward.objects.create(
            show=self.show, assignment=assignment, session=HorseShowAward.Session.MORNING,
        )
        afternoon = HorseShowAward.objects.create(
            show=self.show, assignment=assignment, session=HorseShowAward.Session.AFTERNOON,
        )
        self.assertEqual(morning.horse, self.horse)
        self.assertEqual(afternoon.horse, self.horse)
        self.assertEqual(self.show.horse_awards.count(), 2)

    def test_horse_profile_shows_award_history(self):
        assignment = HorseShowAssignment.objects.create(show=self.show, horse=self.horse)
        HorseShowAward.objects.create(
            show=self.show, assignment=assignment, session=HorseShowAward.Session.FULL_DAY,
        )
        self.client.login(username="horserider211", password="testpass123")
        response = self.client.get(reverse("horse_detail", args=[self.horse.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Horse of the Day history")
        self.assertContains(response, "Full Day Horse of the Day")
