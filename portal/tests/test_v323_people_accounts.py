from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from portal.forms import UserAccountEditForm, UserOnboardingForm
from portal.model_modules.people import LegacyPersonLink, Person
from portal.models import GuardianContact, Rider, Team, UserProfile
from portal.people_compat import ensure_guardian_person, ensure_rider_person


@override_settings(DEFAULT_TEMP_PASSWORD="TemporaryPass!2026")
class V323PeopleAccountTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
        self.admin = User.objects.create_user(username="account-admin", password="pass12345")
        profile = self.admin.profile
        profile.team = self.team
        profile.role = UserProfile.Role.ADMIN
        profile.save(update_fields=["team", "role"])

    def test_rider_onboarding_reuses_canonical_person_and_links_login(self):
        rider = Rider.objects.create(
            team=self.team, first_name="Jamie", last_name="Smith", email="jamie@example.com", grade=7
        )
        person = ensure_rider_person(rider)
        form = UserOnboardingForm(
            data={
                "first_name": "Jamie",
                "last_name": "Smith",
                "email": "jamie@example.com",
                "username": "jamie.smith",
                "role": UserProfile.Role.RIDER,
                "rider": rider.pk,
                "guardian": "",
                "temporary_password": "TemporaryPass!2026",
            },
            team=self.team,
            actor=self.admin,
        )
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        person.refresh_from_db()
        self.assertEqual(person.user_id, user.id)
        self.assertEqual(user.arena_person.pk, person.pk)
        self.assertEqual(rider.user_id, user.id)

    def test_parent_onboarding_reuses_canonical_person_and_links_login(self):
        guardian = GuardianContact.objects.create(
            team=self.team, first_name="Morgan", last_name="Smith", email="morgan@example.com"
        )
        person = ensure_guardian_person(guardian)
        form = UserOnboardingForm(
            data={
                "first_name": "Morgan",
                "last_name": "Smith",
                "email": "morgan@example.com",
                "username": "morgan.smith",
                "role": UserProfile.Role.PARENT,
                "rider": "",
                "guardian": guardian.pk,
                "temporary_password": "TemporaryPass!2026",
            },
            team=self.team,
            actor=self.admin,
        )
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        person.refresh_from_db()
        self.assertEqual(person.user_id, user.id)
        self.assertEqual(user.arena_person.pk, person.pk)
        self.assertEqual(guardian.user_id, user.id)

    def test_staff_onboarding_creates_person_even_without_legacy_identity(self):
        form = UserOnboardingForm(
            data={
                "first_name": "Casey",
                "last_name": "Coach",
                "email": "casey@example.com",
                "username": "casey.coach",
                "role": UserProfile.Role.COACH,
                "rider": "",
                "guardian": "",
                "temporary_password": "TemporaryPass!2026",
            },
            team=self.team,
            actor=self.admin,
        )
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        person = user.arena_person
        self.assertEqual(person.team_id, self.team.id)
        self.assertEqual(person.first_name, "Casey")
        self.assertEqual(person.last_name, "Coach")
        self.assertFalse(LegacyPersonLink.objects.filter(person=person).exists())

    def test_account_edit_keeps_person_identity_and_syncs_contact_fields(self):
        rider = Rider.objects.create(team=self.team, first_name="Jamie", last_name="Smith", grade=7)
        person = ensure_rider_person(rider)
        user = User.objects.create_user(
            username="jamie.edit", password="pass12345", first_name="Jamie", last_name="Smith", email="old@example.com"
        )
        profile = user.profile
        profile.team = self.team
        profile.role = UserProfile.Role.RIDER
        profile.save(update_fields=["team", "role"])
        rider.user = user
        rider.save(update_fields=["user"])
        person.user = user
        person.save(update_fields=["user"])

        form = UserAccountEditForm(
            data={
                "first_name": "Jamie",
                "last_name": "Smith",
                "email": "new@example.com",
                "role": UserProfile.Role.RIDER,
                "is_active": "on",
                "rider": rider.pk,
                "guardian": "",
            },
            team=self.team,
            actor=self.admin,
            user_obj=user,
        )
        self.assertTrue(form.is_valid(), form.errors)
        saved = form.save()
        person.refresh_from_db()
        self.assertEqual(saved.arena_person.pk, person.pk)
        self.assertEqual(person.email, "new@example.com")

    def test_existing_person_cannot_be_silently_replaced_by_another_legacy_identity(self):
        rider_a = Rider.objects.create(team=self.team, first_name="Alex", last_name="One", grade=7)
        rider_b = Rider.objects.create(team=self.team, first_name="Alex", last_name="Two", grade=8)
        person_a = ensure_rider_person(rider_a)
        ensure_rider_person(rider_b)
        user = User.objects.create_user(username="alex.one", password="pass12345")
        profile = user.profile
        profile.team = self.team
        profile.role = UserProfile.Role.RIDER
        profile.save(update_fields=["team", "role"])
        rider_a.user = user
        rider_a.save(update_fields=["user"])
        person_a.user = user
        person_a.save(update_fields=["user"])
        self.assertEqual(Person.objects.filter(user=user).count(), 1)
