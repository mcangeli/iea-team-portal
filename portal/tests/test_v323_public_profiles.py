from django.test import TestCase
from django.urls import reverse

from portal.model_modules.people import LegacyPersonLink, Person
from portal.model_modules.public_site import PublicSiteProfile
from portal.models import Rider, Team
from portal.public_profiles import public_profile_for_person, public_profile_for_rider


class V323PublicProfileTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
        self.site = PublicSiteProfile.objects.create(
            team=self.team,
            slug="blue-skies",
            enabled=True,
            display_name="Blue Skies Riding Academy",
        )
        self.rider = Rider.objects.create(
            team=self.team,
            first_name="Jamie",
            last_name="Smith",
            grade=7,
            school="Private School",
            email="jamie@example.com",
        )
        self.person = Person.objects.create(
            team=self.team,
            first_name="Jamie",
            last_name="Smith",
            preferred_name="Jay",
            email="private@example.com",
            phone="555-0100",
            school="Private School",
            graduation_year=2031,
            bio="I love riding and helping at the barn.",
            instagram_url="https://instagram.com/jayrides",
            youtube_url="https://youtube.com/@jayrides",
            public_profile_enabled=True,
        )
        LegacyPersonLink.objects.create(person=self.person, rider=self.rider)

    def test_opted_in_profile_contains_only_approved_public_fields(self):
        profile = public_profile_for_person(self.person)
        self.assertEqual(profile["display_name"], "Jay Smith")
        self.assertEqual(profile["bio"], self.person.bio)
        self.assertEqual(profile["instagram_url"], self.person.instagram_url)
        self.assertEqual(profile["youtube_url"], self.person.youtube_url)
        for private_field in (
            "email", "phone", "birth_date", "school", "graduation_year",
            "facebook_url", "tiktok_url", "family", "roles",
        ):
            self.assertNotIn(private_field, profile)

    def test_public_profile_requires_explicit_opt_in(self):
        self.person.public_profile_enabled = False
        self.person.save(update_fields=["public_profile_enabled"])
        self.assertIsNone(public_profile_for_person(self.person))
        self.assertIsNone(public_profile_for_rider(self.rider))

    def test_inactive_person_is_never_public(self):
        self.person.active = False
        self.person.save(update_fields=["active"])
        self.assertIsNone(public_profile_for_rider(self.rider))

    def test_public_home_surfaces_opted_in_rider_card(self):
        response = self.client.get(reverse("public_site_home", args=[self.site.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Jay Smith")
        self.assertContains(response, "View rider card")
        self.assertNotContains(response, "Private School")
        self.assertNotContains(response, "private@example.com")

    def test_public_riders_directory_and_detail_are_anonymous(self):
        directory = self.client.get(reverse("public_riders", args=[self.site.slug]))
        self.assertEqual(directory.status_code, 200)
        self.assertContains(directory, "Jay Smith")
        detail = self.client.get(reverse("public_rider_detail", args=[self.site.slug, self.person.pk]))
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "Jay Smith")
        self.assertContains(detail, self.person.bio)
        self.assertNotContains(detail, "Private School")
        self.assertNotContains(detail, "private@example.com")

    def test_public_rider_detail_disappears_when_opt_out_is_disabled(self):
        url = reverse("public_rider_detail", args=[self.site.slug, self.person.pk])
        self.person.public_profile_enabled = False
        self.person.save(update_fields=["public_profile_enabled"])
        self.assertEqual(self.client.get(url).status_code, 404)
        directory = self.client.get(reverse("public_riders", args=[self.site.slug]))
        self.assertNotContains(directory, "Jay Smith")
