from datetime import date

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from portal.models import (
    CommitteeAssignment,
    GuardianContact,
    Notification,
    Rider,
    RiderGuardian,
    Season,
    SeasonMembership,
    Show,
    ShowClass,
    ShowDayUpdate,
    ShowEntry,
    Team,
    UserProfile,
)
from portal.views import _show_update_allowed_audiences


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    EMAIL_HOST="mail.test",
    DEFAULT_FROM_EMAIL="portal@test.invalid",
)
class ShowDayUpdateTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Test Team", short_name="TT")
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
            name="Fall IEA Show",
            show_date=date(2026, 10, 10),
            status=Show.Status.ENTERED,
        )
        self.show_class = ShowClass.objects.create(
            show=self.show,
            name="Beginner Flat",
            class_number="H10",
            sort_order=1,
        )

        self.coach = self.make_user("coach", UserProfile.Role.COACH, "coach@example.com")
        self.futures_parent_chair = self.make_user("futureschair", UserProfile.Role.PARENT, "futureschair@example.com")
        self.upper_parent_chair = self.make_user("upperchair", UserProfile.Role.PARENT, "upperchair@example.com")
        CommitteeAssignment.objects.create(
            team=self.team, season=self.season, user=self.futures_parent_chair,
            role=CommitteeAssignment.Role.FUTURES_PARENT, active=True,
        )
        CommitteeAssignment.objects.create(
            team=self.team, season=self.season, user=self.upper_parent_chair,
            role=CommitteeAssignment.Role.UPPER_PARENT, active=True,
        )

        self.futures_rider_user = self.make_user("futuresrider", UserProfile.Role.RIDER, "futuresrider@example.com")
        self.futures_parent = self.make_user("futuresparent", UserProfile.Role.PARENT, "futuresparent@example.com")
        self.futures_rider = Rider.objects.create(
            team=self.team, user=self.futures_rider_user,
            first_name="Future", last_name="Rider", grade=7,
        )
        SeasonMembership.objects.create(
            rider=self.futures_rider, season=self.season,
            team_level=SeasonMembership.TeamLevel.FUTURES,
        )
        guardian = GuardianContact.objects.create(
            team=self.team, user=self.futures_parent,
            first_name="Future", last_name="Parent",
        )
        RiderGuardian.objects.create(rider=self.futures_rider, guardian=guardian, relationship="Parent")
        ShowEntry.objects.create(show_class=self.show_class, rider=self.futures_rider)

        self.upper_rider_user = self.make_user("upperrider", UserProfile.Role.RIDER, "upperrider@example.com")
        self.upper_parent = self.make_user("upperparent", UserProfile.Role.PARENT, "upperparent@example.com")
        self.upper_rider = Rider.objects.create(
            team=self.team, user=self.upper_rider_user,
            first_name="Upper", last_name="Rider", grade=10,
        )
        SeasonMembership.objects.create(
            rider=self.upper_rider, season=self.season,
            team_level=SeasonMembership.TeamLevel.UPPER,
        )
        guardian = GuardianContact.objects.create(
            team=self.team, user=self.upper_parent,
            first_name="Upper", last_name="Parent",
        )
        RiderGuardian.objects.create(rider=self.upper_rider, guardian=guardian, relationship="Parent")
        ShowEntry.objects.create(show_class=self.show_class, rider=self.upper_rider)

    def make_user(self, username, role, email=""):
        user = User.objects.create_user(username=username, password="testpass", email=email)
        user.profile.team = self.team
        user.profile.role = role
        user.profile.save(update_fields=["team", "role"])
        return user

    def test_futures_team_parent_can_publish_only_futures_updates(self):
        allowed = _show_update_allowed_audiences(self.futures_parent_chair, self.show)
        self.assertEqual(allowed, {ShowDayUpdate.Audience.FUTURES})

        self.client.force_login(self.futures_parent_chair)
        response = self.client.post(reverse("show_day_update_add", args=[self.show.pk]), {
            "audience": ShowDayUpdate.Audience.FUTURES,
            "title": "Ring running behind",
            "body": "Futures classes are running about 20 minutes behind.",
            "send_email": "on",
            "published": "on",
            "notify_now": "on",
        })
        self.assertEqual(response.status_code, 302)
        update = ShowDayUpdate.objects.get(title="Ring running behind")
        self.assertEqual(update.created_by, self.futures_parent_chair)

        notified = set(Notification.objects.filter(show_day_update=update).values_list("user__username", flat=True))
        self.assertIn("futuresparent", notified)
        self.assertIn("futuresrider", notified)
        self.assertIn("futureschair", notified)
        self.assertIn("coach", notified)
        self.assertNotIn("upperparent", notified)
        self.assertNotIn("upperrider", notified)
        self.assertNotIn("upperchair", notified)

    def test_futures_parent_cannot_post_upper_or_everyone_update(self):
        self.client.force_login(self.futures_parent_chair)
        for audience in [ShowDayUpdate.Audience.UPPER, ShowDayUpdate.Audience.ALL]:
            response = self.client.post(reverse("show_day_update_add", args=[self.show.pk]), {
                "audience": audience,
                "title": "Not allowed",
                "body": "Wrong audience",
                "published": "on",
                "notify_now": "on",
            })
            self.assertEqual(response.status_code, 200)
            self.assertFalse(ShowDayUpdate.objects.filter(title="Not allowed").exists())

    def test_upper_parent_cannot_edit_futures_update(self):
        update = ShowDayUpdate.objects.create(
            show=self.show, audience=ShowDayUpdate.Audience.FUTURES,
            title="Futures note", body="Original", created_by=self.coach, updated_by=self.coach,
        )
        self.client.force_login(self.upper_parent_chair)
        response = self.client.get(reverse("show_day_update_edit", args=[update.pk]))
        self.assertEqual(response.status_code, 403)

    def test_edit_can_republish_without_notification_or_renotify(self):
        update = ShowDayUpdate.objects.create(
            show=self.show, audience=ShowDayUpdate.Audience.FUTURES,
            title="Timing", body="About 15 minutes behind.", created_by=self.coach, updated_by=self.coach,
        )
        self.client.force_login(self.futures_parent_chair)
        response = self.client.post(reverse("show_day_update_edit", args=[update.pk]), {
            "audience": ShowDayUpdate.Audience.FUTURES,
            "title": "Timing",
            "body": "Now about 25 minutes behind.",
            "send_email": "on",
            "published": "on",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Notification.objects.filter(show_day_update=update).count(), 0)

        response = self.client.post(reverse("show_day_update_edit", args=[update.pk]), {
            "audience": ShowDayUpdate.Audience.FUTURES,
            "title": "Timing",
            "body": "Now about 30 minutes behind.",
            "send_email": "on",
            "published": "on",
            "notify_now": "on",
        })
        self.assertEqual(response.status_code, 302)
        self.assertGreater(Notification.objects.filter(show_day_update=update).count(), 0)
        self.assertTrue(Notification.objects.filter(show_day_update=update, title__startswith="Updated:").exists())

    def test_show_update_email_respects_separate_preference(self):
        self.futures_parent.profile.email_show_updates = False
        self.futures_parent.profile.save(update_fields=["email_show_updates"])
        self.client.force_login(self.futures_parent_chair)
        response = self.client.post(reverse("show_day_update_add", args=[self.show.pk]), {
            "audience": ShowDayUpdate.Audience.FUTURES,
            "title": "Parking update",
            "body": "Use the south lot.",
            "send_email": "on",
            "published": "on",
            "notify_now": "on",
        })
        self.assertEqual(response.status_code, 302)
        recipients = {address for message in mail.outbox for address in message.to}
        self.assertNotIn("futuresparent@example.com", recipients)
        self.assertIn("futureschair@example.com", recipients)

    def test_rider_cannot_gain_publish_rights_from_bad_committee_assignment(self):
        CommitteeAssignment.objects.create(
            team=self.team, season=self.season, user=self.futures_rider_user,
            role=CommitteeAssignment.Role.FUTURES_PARENT, active=True,
        )
        self.assertEqual(_show_update_allowed_audiences(self.futures_rider_user, self.show), set())
        self.client.force_login(self.futures_rider_user)
        self.assertEqual(self.client.get(reverse("show_day_update_add", args=[self.show.pk])).status_code, 403)

    def test_public_feed_is_scoped_to_relevant_family(self):
        futures_update = ShowDayUpdate.objects.create(
            show=self.show, audience=ShowDayUpdate.Audience.FUTURES,
            title="Futures schedule", body="Futures message", created_by=self.coach,
        )
        ShowDayUpdate.objects.create(
            show=self.show, audience=ShowDayUpdate.Audience.UPPER,
            title="Upper schedule", body="Upper message", created_by=self.coach,
        )
        self.client.force_login(self.futures_parent)
        response = self.client.get(reverse("show_day_updates", args=[self.show.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, futures_update.title)
        self.assertNotContains(response, "Upper schedule")
