from django.test import TestCase

from portal.model_modules.people import LegacyPersonLink, Person
from portal.models import Rider, Team
from portal.public_profiles import public_profile_for_person, public_profile_for_rider


class V323PublicProfileTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
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
