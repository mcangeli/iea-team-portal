from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from portal.account_security import (
    begin_email_verification,
    make_email_verification_token,
)
from portal.models import Rider, Team, UserProfile


class EmailVerificationTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Account Security Test")
        self.user = User.objects.create_user(
            username="secure-parent", password="safe-password-123",
            email="old@example.com",
        )
        self.user.profile.team = self.team
        self.user.profile.role = UserProfile.Role.PARENT
        self.user.profile.email_verified_at = timezone.now()
        self.user.profile.must_change_password = False
        self.user.profile.save()
        self.client = Client()
        self.client.force_login(self.user)

    @patch("portal.account_views.send_email_verification")
    def test_change_email_requires_current_password_and_keeps_current_email(self, send_verification):
        response = self.client.post(reverse("email_change"), {
            "email": "new@example.com", "current_password": "wrong",
        })
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "old@example.com")
        self.assertEqual(self.user.profile.pending_email, "")

        response = self.client.post(reverse("email_change"), {
            "email": "new@example.com", "current_password": "safe-password-123",
        })
        self.assertRedirects(response, reverse("my_account"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "old@example.com")
        self.assertEqual(self.user.profile.pending_email, "new@example.com")
        send_verification.assert_called_once()

    def test_valid_token_promotes_pending_email(self):
        begin_email_verification(self.user, "new@example.com")
        token = make_email_verification_token(self.user)
        response = self.client.get(reverse("email_verify", kwargs={"token": token}))
        self.assertRedirects(response, reverse("my_account"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "new@example.com")
        self.assertEqual(self.user.profile.pending_email, "")
        self.assertIsNotNone(self.user.profile.email_verified_at)

    def test_invalid_or_wrong_account_token_does_not_change_email(self):
        response = self.client.get(reverse("email_verify", kwargs={"token": "not-a-valid-token"}))
        self.assertRedirects(response, reverse("my_account"))
        other = User.objects.create_user(username="other", password="safe-password-123", email="other@example.com")
        other.profile.team = self.team
        other.profile.pending_email = "other-new@example.com"
        other.profile.save()
        token = make_email_verification_token(other)
        response = self.client.get(reverse("email_verify", kwargs={"token": token}))
        self.assertRedirects(response, reverse("my_account"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "old@example.com")

    def test_stale_token_cannot_replace_newer_pending_request(self):
        begin_email_verification(self.user, "first@example.com")
        stale = make_email_verification_token(self.user)
        begin_email_verification(self.user, "second@example.com")
        response = self.client.get(reverse("email_verify", kwargs={"token": stale}))
        self.assertRedirects(response, reverse("my_account"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "old@example.com")
        self.assertEqual(self.user.profile.pending_email, "second@example.com")

    @patch("portal.account_views.send_email_verification", return_value=True)
    def test_resend_uses_existing_verification_state(self, send_verification):
        response = self.client.post(reverse("email_verification_resend"))
        self.assertRedirects(response, reverse("my_account"))
        send_verification.assert_called_once()

    def test_verification_synchronizes_legacy_contact_records(self):
        Rider.objects.create(team=self.team, user=self.user, first_name="Secure", last_name="Parent", email="old@example.com")
        begin_email_verification(self.user, "new@example.com")
        token = make_email_verification_token(self.user)
        self.client.get(reverse("email_verify", kwargs={"token": token}))
        self.user.rider_record.refresh_from_db()
        self.assertEqual(self.user.rider_record.email, "new@example.com")

    def test_my_account_shows_verified_and_pending_states(self):
        response = self.client.get(reverse("my_account"))
        self.assertContains(response, "Verified")
        begin_email_verification(self.user, "pending@example.com")
        response = self.client.get(reverse("my_account"))
        self.assertContains(response, "pending@example.com")
        self.assertContains(response, "Resend verification")


    def test_profile_edit_cannot_bypass_verified_email_change(self):
        response = self.client.get(reverse("my_account_edit"))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("email", response.context["form"].fields)

    def test_duplicate_email_is_rejected_case_insensitively(self):
        User.objects.create_user(username="duplicate", email="Taken@Example.com", password="safe-password-123")
        response = self.client.post(reverse("email_change"), {
            "email": "taken@example.com", "current_password": "safe-password-123",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already associated with another ArenaLine account")
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.pending_email, "")

    @patch("portal.account_views.send_email_verification", side_effect=RuntimeError("mail unavailable"))
    def test_mail_failure_rolls_back_pending_email(self, send_verification):
        response = self.client.post(reverse("email_change"), {
            "email": "new@example.com", "current_password": "safe-password-123",
        })
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.email, "old@example.com")
        self.assertEqual(self.user.profile.pending_email, "")
        self.assertContains(response, "could not send the verification email")

    def test_completed_verification_token_cannot_be_replayed(self):
        begin_email_verification(self.user, "new@example.com")
        token = make_email_verification_token(self.user)
        self.client.get(reverse("email_verify", kwargs={"token": token}))
        self.user.profile.refresh_from_db()
        first_verified_at = self.user.profile.email_verified_at

        response = self.client.get(reverse("email_verify", kwargs={"token": token}))
        self.assertRedirects(response, reverse("my_account"))
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.email_verified_at, first_verified_at)

    def test_unverified_current_email_can_be_verified(self):
        self.user.profile.email_verified_at = None
        self.user.profile.pending_email = ""
        self.user.profile.save(update_fields=["email_verified_at", "pending_email"])
        token = make_email_verification_token(self.user)
        response = self.client.get(reverse("email_verify", kwargs={"token": token}))
        self.assertRedirects(response, reverse("my_account"))
        self.user.profile.refresh_from_db()
        self.assertIsNotNone(self.user.profile.email_verified_at)
