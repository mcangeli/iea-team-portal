from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from portal.models import (
    ActionItem,
    CalendarEvent,
    Lesson,
    LessonAttendance,
    Notification,
    Rider,
    Season,
    SeasonMembership,
    Team,
    UserProfile,
    VolunteerLog,
)


class Preview5OperationsAccessTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Organization A")
        self.other_team = Team.objects.create(name="Organization B")
        self.season = Season.objects.create(
            team=self.team,
            name="2026-27",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 7, 31),
            is_active=True,
        )
        self.other_season = Season.objects.create(
            team=self.other_team,
            name="2026-27",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 7, 31),
            is_active=True,
        )

        self.parent = self.make_user("parent-a", UserProfile.Role.PARENT, self.team)
        self.admin = self.make_user("admin-a", UserProfile.Role.ADMIN, self.team)
        self.other_user = self.make_user("parent-b", UserProfile.Role.PARENT, self.other_team)

        self.rider = Rider.objects.create(
            team=self.team, first_name="Emma", last_name="Brown", grade=7
        )
        self.other_rider_same_team = Rider.objects.create(
            team=self.team, first_name="Taylor", last_name="Smith", grade=10
        )
        self.foreign_rider = Rider.objects.create(
            team=self.other_team, first_name="Morgan", last_name="Jones", grade=8
        )
        self.rider.guardians.add(self.parent)
        SeasonMembership.objects.create(
            rider=self.rider,
            season=self.season,
            team_level=SeasonMembership.TeamLevel.FUTURES,
        )
        SeasonMembership.objects.create(
            rider=self.other_rider_same_team,
            season=self.season,
            team_level=SeasonMembership.TeamLevel.UPPER,
        )
        SeasonMembership.objects.create(
            rider=self.foreign_rider,
            season=self.other_season,
            team_level=SeasonMembership.TeamLevel.FUTURES,
        )

        now = timezone.now()
        self.public_event = CalendarEvent.objects.create(
            team=self.team,
            season=self.season,
            title="Team Meeting",
            starts_at=now,
            visible_to_all=True,
            rsvp_requested=True,
        )
        self.private_event = CalendarEvent.objects.create(
            team=self.team,
            season=self.season,
            title="Coach Planning",
            starts_at=now,
            visible_to_all=False,
        )
        self.foreign_event = CalendarEvent.objects.create(
            team=self.other_team,
            season=self.other_season,
            title="Other Organization Event",
            starts_at=now,
            visible_to_all=True,
            rsvp_requested=True,
        )

        self.lesson = Lesson.objects.create(
            team=self.team,
            season=self.season,
            title="Futures Lesson",
            starts_at=now,
        )
        LessonAttendance.objects.create(lesson=self.lesson, rider=self.rider)
        self.unrelated_lesson = Lesson.objects.create(
            team=self.team,
            season=self.season,
            title="Upper Lesson",
            starts_at=now,
        )
        LessonAttendance.objects.create(
            lesson=self.unrelated_lesson, rider=self.other_rider_same_team
        )
        self.foreign_lesson = Lesson.objects.create(
            team=self.other_team,
            season=self.other_season,
            title="Other Organization Lesson",
            starts_at=now,
        )

        self.foreign_volunteer = VolunteerLog.objects.create(
            season=self.other_season,
            rider=self.foreign_rider,
            service_date=date(2026, 9, 1),
            hours="2.00",
            description="Show support",
            submitted_by=self.other_user,
        )

        self.private_action = ActionItem.objects.create(
            team=self.team,
            season=self.season,
            title="Manager-only task",
            family_visible=False,
            claimable=True,
            created_by=self.admin,
        )
        self.family_action = ActionItem.objects.create(
            team=self.team,
            season=self.season,
            title="Bring water",
            family_visible=True,
            claimable=True,
            created_by=self.admin,
        )

        self.parent_notification = Notification.objects.create(
            user=self.parent,
            title="Parent notice",
        )
        self.other_notification = Notification.objects.create(
            user=self.other_user,
            title="Other notice",
        )

    def make_user(self, username, role, team):
        user = User.objects.create_user(username=username, password="testpass")
        user.profile.team = team
        user.profile.role = role
        user.profile.save(update_fields=["team", "role"])
        return user

    def test_private_calendar_event_is_not_visible_to_parent(self):
        self.client.force_login(self.parent)
        response = self.client.get(reverse("event_detail", args=[self.private_event.pk]))
        self.assertEqual(response.status_code, 403)

    def test_foreign_calendar_event_is_not_disclosed(self):
        self.client.force_login(self.parent)
        response = self.client.get(reverse("event_detail", args=[self.foreign_event.pk]))
        self.assertEqual(response.status_code, 404)

    def test_parent_can_rsvp_only_for_linked_rider(self):
        self.client.force_login(self.parent)
        allowed = self.client.post(
            reverse("event_rsvp", args=[self.public_event.pk, self.rider.pk]),
            {"status": "going", "notes": ""},
        )
        self.assertEqual(allowed.status_code, 302)

        denied = self.client.post(
            reverse(
                "event_rsvp",
                args=[self.public_event.pk, self.other_rider_same_team.pk],
            ),
            {"status": "going", "notes": ""},
        )
        self.assertEqual(denied.status_code, 404)

        foreign = self.client.post(
            reverse("event_rsvp", args=[self.foreign_event.pk, self.foreign_rider.pk]),
            {"status": "going", "notes": ""},
        )
        self.assertEqual(foreign.status_code, 404)

    def test_parent_lesson_detail_is_limited_to_linked_riders(self):
        self.client.force_login(self.parent)
        allowed = self.client.get(reverse("lesson_detail", args=[self.lesson.pk]))
        self.assertEqual(allowed.status_code, 200)

        denied = self.client.get(reverse("lesson_detail", args=[self.unrelated_lesson.pk]))
        self.assertEqual(denied.status_code, 403)

        foreign = self.client.get(reverse("lesson_detail", args=[self.foreign_lesson.pk]))
        self.assertEqual(foreign.status_code, 404)

    def test_parent_cannot_review_volunteer_entries(self):
        self.client.force_login(self.parent)
        response = self.client.post(
            reverse("volunteer_review", args=[self.foreign_volunteer.pk]),
            {"status": VolunteerLog.Status.APPROVED, "coach_notes": ""},
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_cannot_review_foreign_volunteer_entry(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("volunteer_review", args=[self.foreign_volunteer.pk]),
            {"status": VolunteerLog.Status.APPROVED, "coach_notes": ""},
        )
        self.assertEqual(response.status_code, 404)

    def test_hidden_action_item_cannot_be_claimed_by_parent(self):
        self.client.force_login(self.parent)
        response = self.client.post(reverse("action_item_claim", args=[self.private_action.pk]))
        self.assertEqual(response.status_code, 404)

    def test_family_visible_claimable_action_item_can_be_claimed(self):
        self.client.force_login(self.parent)
        response = self.client.post(reverse("action_item_claim", args=[self.family_action.pk]))
        self.assertEqual(response.status_code, 302)
        self.family_action.refresh_from_db()
        self.assertEqual(self.family_action.claimed_by_id, self.parent.id)

    def test_notification_read_is_user_scoped(self):
        self.client.force_login(self.parent)
        response = self.client.post(reverse("notification_read", args=[self.other_notification.pk]))
        self.assertEqual(response.status_code, 404)
        self.other_notification.refresh_from_db()
        self.assertIsNone(self.other_notification.read_at)

        own = self.client.post(reverse("notification_read", args=[self.parent_notification.pk]))
        self.assertEqual(own.status_code, 302)
        self.parent_notification.refresh_from_db()
        self.assertIsNotNone(self.parent_notification.read_at)
