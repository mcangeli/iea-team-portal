from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.public_site import PublicShowPublication
from portal.model_modules.show_day_state import ShowClassLiveState
from portal.models import (
    Rider,
    Season,
    SeasonClass,
    Show,
    ShowClass,
    ShowEntry,
    ShowResult,
    Team,
    UserProfile,
)
from portal.publication import public_show_results_payload


class ClassResultPublicationTests(TestCase):
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
            status=Show.Status.IN_PROGRESS,
        )
        season_class = SeasonClass.objects.create(
            season=self.season,
            name="Futures Flat",
            team_level=SeasonClass.TeamLevel.FUTURES,
        )
        self.show_class = ShowClass.objects.create(
            show=self.show,
            season_class=season_class,
            name="Futures Flat",
            class_number="H10",
            sort_order=1,
        )
        rider = Rider.objects.create(
            team=self.team,
            first_name="Emma",
            last_name="Brown",
            grade=7,
        )
        self.entry = ShowEntry.objects.create(
            show_class=self.show_class,
            rider=rider,
            status=ShowEntry.Status.ENTERED,
        )
        self.state = ShowClassLiveState.objects.create(
            show_class=self.show_class,
            status=ShowClassLiveState.Status.COMPLETE,
        )
        self.publication = PublicShowPublication.objects.create(
            show=self.show,
            slug="autumn-invitational-results",
            is_published=True,
            publish_results=False,
        )
        self.admin = User.objects.create_user(username="results-admin", password="testpass")
        self.admin.profile.team = self.team
        self.admin.profile.role = UserProfile.Role.ADMIN
        self.admin.profile.save(update_fields=["team", "role"])

    def publish(self, value="1"):
        self.client.force_login(self.admin)
        return self.client.post(
            reverse("show_class_results_publication_update", args=[self.show_class.pk]),
            {"publish": value},
        )

    def test_completed_class_requires_a_placing_before_publication(self):
        response = self.publish()
        self.assertEqual(response.status_code, 302)
        self.state.refresh_from_db()
        self.assertFalse(self.state.results_published)

    def test_publish_and_unpublish_class_results(self):
        ShowResult.objects.create(entry=self.entry, place=1)

        response = self.publish()
        self.assertEqual(response.status_code, 302)
        self.state.refresh_from_db()
        self.publication.refresh_from_db()
        self.assertTrue(self.state.results_published)
        self.assertTrue(self.publication.publish_results)

        payload = public_show_results_payload(self.publication)
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["results"][0]["place_label"], "1st")
        self.assertEqual(payload[0]["results"][0]["place_class"], "place-1")

        self.publish("0")
        self.state.refresh_from_db()
        self.assertFalse(self.state.results_published)
        self.assertEqual(public_show_results_payload(self.publication), [])

    def test_placement_metadata_supports_equestrian_ribbon_order(self):
        ShowResult.objects.create(entry=self.entry, place=3)
        self.state.results_published = True
        self.state.save(update_fields=["results_published"])
        self.publication.publish_results = True
        self.publication.save(update_fields=["publish_results"])

        result = public_show_results_payload(self.publication)[0]["results"][0]
        self.assertEqual(result["place_label"], "3rd")
        self.assertEqual(result["place_class"], "place-3")
