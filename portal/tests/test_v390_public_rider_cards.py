from django.test import TestCase
from django.urls import reverse

from portal.model_modules.people import IEAParticipant, Person
from portal.model_modules.public_site import PublicSiteProfile
from portal.models import Team
from portal.public_profiles import public_profile_for_team_person, public_profiles_for_team


class V390PublicRiderCardTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
        self.site = PublicSiteProfile.objects.create(
            team=self.team,
            slug="blue-skies-v390",
            enabled=True,
            display_name="Blue Skies Riding Academy",
        )
        self.person = Person.objects.create(
            team=self.team,
            first_name="Alex",
            last_name="Morgan",
            preferred_name="Alex",
            bio="ArenaLine rider profile.",
            public_profile_enabled=True,
        )
        self.participant = IEAParticipant.objects.create(
            team=self.team,
            person=self.person,
            active=True,
        )

    def test_person_native_iea_participant_is_public_without_legacy_rider(self):
        profiles = public_profiles_for_team(self.team)
        self.assertEqual([profile["person_id"] for profile in profiles], [self.person.pk])
        self.assertEqual(profiles[0]["display_name"], "Alex Morgan")

    def test_person_native_public_detail_resolves_by_person(self):
        profile = public_profile_for_team_person(self.team, self.person.pk)
        self.assertIsNotNone(profile)
        self.assertEqual(profile["person_id"], self.person.pk)
        self.assertEqual(profile["bio"], self.person.bio)

    def test_person_native_public_routes_do_not_require_legacy_rider(self):
        directory = self.client.get(reverse("public_riders", args=[self.site.slug]))
        self.assertEqual(directory.status_code, 200)
        self.assertContains(directory, "Alex Morgan")

        detail = self.client.get(
            reverse("public_rider_detail", args=[self.site.slug, self.person.pk])
        )
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "Alex Morgan")
        self.assertContains(detail, self.person.bio)

    def test_opt_out_still_hides_person_native_rider_card(self):
        self.person.public_profile_enabled = False
        self.person.save(update_fields=["public_profile_enabled"])

        self.assertEqual(public_profiles_for_team(self.team), [])
        self.assertIsNone(public_profile_for_team_person(self.team, self.person.pk))
        detail = self.client.get(
            reverse("public_rider_detail", args=[self.site.slug, self.person.pk])
        )
        self.assertEqual(detail.status_code, 404)

    def test_inactive_iea_participant_is_not_public_rider_card(self):
        self.participant.active = False
        self.participant.save(update_fields=["active"])

        self.assertEqual(public_profiles_for_team(self.team), [])
        self.assertIsNone(public_profile_for_team_person(self.team, self.person.pk))
