from datetime import date, time

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.models import (
    Rider,
    Season,
    SeasonMembership,
    Show,
    ShowClass,
    ShowDayRiderStatus,
    ShowEntry,
    ShowPlanningItem,
    Team,
    UserProfile,
)


class MyShowDayTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Test Team")
        self.season = Season.objects.create(
            team=self.team,
            name="2026-27",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 7, 31),
            is_active=True,
        )
        self.show = Show.objects.create(
            team=self.team,
            season=self.season,
            name="Fall Show",
            show_date=date(2026, 10, 10),
        )

        self.parent = User.objects.create_user(
            username="parent", password="testpass"
        )
        self.parent.profile.team = self.team
        self.parent.profile.role = UserProfile.Role.PARENT
        self.parent.profile.save(update_fields=["team", "role"])

        self.other_parent = User.objects.create_user(
            username="otherparent", password="testpass"
        )
        self.other_parent.profile.team = self.team
        self.other_parent.profile.role = UserProfile.Role.PARENT
        self.other_parent.profile.save(update_fields=["team", "role"])

        self.rider = Rider.objects.create(
            team=self.team,
            first_name="Emma",
            last_name="Brown",
            grade=7,
        )
        self.rider.guardians.add(self.parent)
        SeasonMembership.objects.create(
            rider=self.rider,
            season=self.season,
            team_level=SeasonMembership.TeamLevel.FUTURES,
        )

        self.other_rider = Rider.objects.create(
            team=self.team,
            first_name="Taylor",
            last_name="Smith",
            grade=10,
        )
        self.other_rider.guardians.add(self.other_parent)
        SeasonMembership.objects.create(
            rider=self.other_rider,
            season=self.season,
            team_level=SeasonMembership.TeamLevel.UPPER,
        )

        self.my_class = ShowClass.objects.create(
            show=self.show,
            name="Intermediate Flat",
            class_number="H12",
            sort_order=10,
            estimated_time=time(10, 5),
        )
        self.other_class = ShowClass.objects.create(
            show=self.show,
            name="Varsity Open Flat",
            class_number="H20",
            sort_order=20,
            estimated_time=time(11, 15),
        )
        ShowEntry.objects.create(
            show_class=self.my_class,
            rider=self.rider,
            status=ShowEntry.Status.ENTERED,
        )
        ShowEntry.objects.create(
            show_class=self.other_class,
            rider=self.other_rider,
            status=ShowEntry.Status.ENTERED,
        )

    def test_parent_sees_only_linked_rider_and_classes(self):
        self.client.force_login(self.parent)
        response = self.client.get(reverse("my_show_day", args=[self.show.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Emma")
        self.assertContains(response, "Intermediate Flat")
        self.assertNotContains(response, "Taylor")
        self.assertNotContains(response, "Varsity Open Flat")

    def test_parent_can_update_linked_rider_and_return_to_my_show_day(self):
        self.client.force_login(self.parent)
        response = self.client.post(
            reverse(
                "show_day_rider_status_update",
                args=[self.show.pk, self.rider.pk],
            ),
            {
                "status": ShowDayRiderStatus.Status.ARRIVED,
                "note": "At the barn",
                "return_to": "my_show_day",
            },
        )
        self.assertRedirects(
            response, reverse("my_show_day", args=[self.show.pk])
        )
        status = ShowDayRiderStatus.objects.get(
            show=self.show, rider=self.rider
        )
        self.assertEqual(status.status, ShowDayRiderStatus.Status.ARRIVED)

    def test_parent_cannot_update_unlinked_rider(self):
        self.client.force_login(self.parent)
        response = self.client.post(
            reverse(
                "show_day_rider_status_update",
                args=[self.show.pk, self.other_rider.pk],
            ),
            {
                "status": ShowDayRiderStatus.Status.ARRIVED,
                "return_to": "my_show_day",
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_claimed_assignment_appears_on_my_show_day(self):
        ShowPlanningItem.objects.create(
            show=self.show,
            item_type=ShowPlanningItem.ItemType.VOLUNTEER,
            team_level=ShowPlanningItem.TeamLevel.FUTURES,
            category=ShowPlanningItem.Category.TASK,
            title="Team lunch helper",
            family_visible=True,
            claimed_by=self.parent,
        )
        self.client.force_login(self.parent)
        response = self.client.get(reverse("my_show_day", args=[self.show.pk]))
        self.assertContains(response, "Team lunch helper")

    def test_unlinked_user_gets_personal_empty_state(self):
        unlinked = User.objects.create_user(
            username="unlinked", password="testpass"
        )
        unlinked.profile.team = self.team
        unlinked.profile.role = UserProfile.Role.PARENT
        unlinked.profile.save(update_fields=["team", "role"])

        self.client.force_login(unlinked)
        response = self.client.get(reverse("my_show_day", args=[self.show.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No rider is linked to this account.")
