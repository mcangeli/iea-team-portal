from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from portal.model_modules.people import LegacyPersonLink, Person
from portal.people_compat import ensure_guardian_contact_for_person
from portal.models import Rider, RiderGuardian, Team, UserProfile


@override_settings(DEFAULT_TEMP_PASSWORD="TemporaryPass!2026")
class V323PeopleAccessUITests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
        self.admin = User.objects.create_user(username="people-access-admin", password="pass12345")
        self.admin.profile.team = self.team
        self.admin.profile.role = UserProfile.Role.ADMIN
        self.admin.profile.save(update_fields=["team", "role"])
        self.person = Person.objects.create(team=self.team, first_name="Casey", last_name="Morgan", email="casey@example.com")
        self.client.force_login(self.admin)

    def test_person_profile_offers_person_first_login_creation(self):
        response = self.client.get(reverse("person_detail", args=[self.person.pk]))
        self.assertContains(response, reverse("person_login_create", args=[self.person.pk]))
        self.assertContains(response, "Create login")

    def test_admin_can_create_login_directly_for_person(self):
        response = self.client.post(reverse("person_login_create", args=[self.person.pk]), {
            "username": "casey.morgan",
            "role": UserProfile.Role.COACH,
            "temporary_password": "TemporaryPass!2026",
        })
        self.assertRedirects(response, reverse("person_detail", args=[self.person.pk]))
        self.person.refresh_from_db()
        self.assertIsNotNone(self.person.user_id)
        self.assertEqual(self.person.user.username, "casey.morgan")
        self.assertEqual(self.person.user.profile.role, UserProfile.Role.COACH)
        self.assertTrue(self.person.user.profile.must_change_password)

    def test_existing_login_routes_to_access_management(self):
        user = User.objects.create_user(username="casey.existing", password="pass12345")
        user.profile.team = self.team
        user.profile.role = UserProfile.Role.PARENT
        user.profile.save(update_fields=["team", "role"])
        self.person.user = user
        self.person.save(update_fields=["user"])
        response = self.client.get(reverse("person_login_create", args=[self.person.pk]))
        self.assertRedirects(response, reverse("user_edit", args=[user.pk]))

    def test_rider_person_login_creation_syncs_legacy_rider_user(self):
        rider = Rider.objects.create(team=self.team, first_name="Riley", last_name="Stone", grade=8)
        rider_person = Person.objects.create(team=self.team, first_name="Riley", last_name="Stone", email="riley@example.com")
        LegacyPersonLink.objects.create(person=rider_person, rider=rider)
        response = self.client.post(reverse("person_login_create", args=[rider_person.pk]), {
            "username": "riley.stone",
            "role": UserProfile.Role.RIDER,
            "temporary_password": "TemporaryPass!2026",
        })
        self.assertRedirects(response, reverse("person_detail", args=[rider_person.pk]))
        rider.refresh_from_db()
        rider_person.refresh_from_db()
        self.assertIsNotNone(rider_person.user_id)
        self.assertEqual(rider.user_id, rider_person.user_id)

    def test_guardian_person_login_creation_syncs_family_access(self):
        rider = Rider.objects.create(team=self.team, first_name="Avery", last_name="Stone", grade=7)
        guardian_person = Person.objects.create(team=self.team, first_name="Morgan", last_name="Stone", email="morgan.stone@example.com")
        guardian = ensure_guardian_contact_for_person(guardian_person)
        RiderGuardian.objects.create(rider=rider, guardian=guardian, relationship="Parent", primary_contact=True)
        response = self.client.post(reverse("person_login_create", args=[guardian_person.pk]), {
            "username": "morgan.stone",
            "role": UserProfile.Role.PARENT,
            "temporary_password": "TemporaryPass!2026",
        })
        self.assertRedirects(response, reverse("person_detail", args=[guardian_person.pk]))
        guardian.refresh_from_db()
        guardian_person.refresh_from_db()
        self.assertIsNotNone(guardian_person.user_id)
        self.assertEqual(guardian.user_id, guardian_person.user_id)
        self.assertTrue(rider.guardians.filter(pk=guardian_person.user_id).exists())
