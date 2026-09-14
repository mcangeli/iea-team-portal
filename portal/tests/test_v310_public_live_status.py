from datetime import date, time

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from portal.forms import ShowForm
from portal.model_modules.public_site import PublicShowPublication, PublicSiteProfile
from portal.models import Season, Show, ShowClass, Team
from portal.public_site_admin import PublicShowPublicationForm


class PublicLiveStatusTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy", short_name="Blue Skies")
        self.season = Season.objects.create(
            team=self.team,
            name="2026-2027",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 6, 30),
            is_active=True,
        )
        self.site = PublicSiteProfile.objects.create(
            team=self.team,
            slug="blue-skies-riding-academy",
            enabled=True,
        )
        self.show = Show.objects.create(
            team=self.team,
            season=self.season,
            name="Autumn Invitational",
            show_date=date(2026, 10, 10),
        )
        self.first = ShowClass.objects.create(
            show=self.show,
            name="Future Beginner Flat",
            class_number="H13",
            sort_order=10,
            estimated_time=time(9, 0),
        )
        self.current = ShowClass.objects.create(
            show=self.show,
            name="Future Novice Flat",
            class_number="H11",
            sort_order=20,
            estimated_time=time(9, 30),
            schedule_note="Ring 1",
        )
        self.last = ShowClass.objects.create(
            show=self.show,
            name="Future Intermediate Flat",
            class_number="H9",
            sort_order=30,
            estimated_time=time(10, 0),
        )
        self.publication = PublicShowPublication.objects.create(
            show=self.show,
            slug="autumn-invitational",
            is_published=True,
            publish_schedule=True,
        )

    def _detail(self):
        return self.client.get(
            reverse("public_show_detail", args=[self.site.slug, self.publication.slug])
        )

    def test_show_form_exposes_live_lifecycle_statuses(self):
        form = ShowForm(instance=self.show)
        choices = dict(form.fields["status"].choices)
        self.assertEqual(choices["in_progress"], "In progress")
        self.assertEqual(choices["paused"], "Paused")

    def test_live_status_is_private_by_default(self):
        self.show.status = "in_progress"
        self.show.save(update_fields=["status"])
        self.publication.current_class = self.current
        self.publication.public_status_note = "Running about 15 minutes behind."
        self.publication.save()

        response = self._detail()
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "In progress")
        self.assertNotContains(response, "Now:")
        self.assertNotContains(response, "Running about 15 minutes behind.")
        self.assertNotContains(response, "Auto-refreshes every 30 seconds")

    def test_published_live_status_derives_completed_current_and_upcoming_classes(self):
        self.show.status = "in_progress"
        self.show.save(update_fields=["status"])
        self.publication.publish_live_status = True
        self.publication.current_class = self.current
        self.publication.public_status_note = "Running about 15 minutes behind."
        self.publication.save()

        response = self._detail()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "In progress")
        self.assertContains(response, "Now: H11 · Future Novice Flat")
        self.assertContains(response, "Running about 15 minutes behind.")
        self.assertContains(response, "Auto-refreshes every 30 seconds")
        self.assertContains(response, '<meta http-equiv="refresh" content="30">', html=True)
        self.assertContains(response, "Complete", count=1)
        self.assertContains(response, "Now", count=2)
        self.assertContains(response, "Upcoming", count=1)

    def test_complete_show_marks_all_published_classes_complete_without_refresh(self):
        self.show.status = "complete"
        self.show.save(update_fields=["status"])
        self.publication.publish_live_status = True
        self.publication.current_class = self.current
        self.publication.save()

        response = self._detail()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Complete", count=4)
        self.assertNotContains(response, "Auto-refreshes every 30 seconds")
        self.assertNotContains(response, 'http-equiv="refresh"')

    def test_pre_show_internal_states_publish_as_upcoming(self):
        self.publication.publish_live_status = True
        self.publication.save(update_fields=["publish_live_status", "updated_at"])

        for status in ("planning", "registration", "entered"):
            self.show.status = status
            self.show.save(update_fields=["status"])
            response = self._detail()
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Upcoming")

    def test_cancelled_show_publishes_cancelled_state(self):
        self.show.status = "cancelled"
        self.show.save(update_fields=["status"])
        self.publication.publish_live_status = True
        self.publication.save(update_fields=["publish_live_status", "updated_at"])

        response = self._detail()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cancelled")
        self.assertNotContains(response, "Auto-refreshes every 30 seconds")

    def test_current_class_must_belong_to_published_show(self):
        other_show = Show.objects.create(
            team=self.team,
            season=self.season,
            name="Other Show",
            show_date=date(2026, 11, 1),
        )
        foreign_class = ShowClass.objects.create(
            show=other_show,
            name="Other Class",
            class_number="H1",
        )
        self.publication.current_class = foreign_class

        with self.assertRaises(ValidationError):
            self.publication.full_clean()

    def test_management_form_only_offers_classes_from_this_show(self):
        other_show = Show.objects.create(
            team=self.team,
            season=self.season,
            name="Other Show",
            show_date=date(2026, 11, 1),
        )
        foreign_class = ShowClass.objects.create(
            show=other_show,
            name="Private Other Show Class",
            class_number="H1",
        )

        form = PublicShowPublicationForm(instance=self.publication, show=self.show)
        choices = form.fields["current_class"].queryset
        self.assertIn(self.current, choices)
        self.assertNotIn(foreign_class, choices)
        self.assertNotIn("public_status", form.fields)
