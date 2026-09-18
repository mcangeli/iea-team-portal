import pyotp
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.mfa import consume_recovery_code, disable_mfa, enable_mfa, generate_recovery_codes, new_totp_secret, verify_totp
from portal.models import Team


class MFAServiceTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="MFA Test Barn")
        self.user = User.objects.create_user(username="mfa-user", email="mfa@example.com", password="secure-test-password")
        self.user.profile.team = self.team
        self.user.profile.save(update_fields=["team"])

    def test_totp_secret_and_code_verify(self):
        secret = new_totp_secret()
        self.assertTrue(verify_totp(secret, pyotp.TOTP(secret).now()))
        self.assertFalse(verify_totp(secret, "000000"))

    def test_enable_mfa_hashes_recovery_codes(self):
        secret = new_totp_secret()
        codes = enable_mfa(self.user.profile, secret, pyotp.TOTP(secret).now())
        self.assertEqual(len(codes), 8)
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.mfa_enabled)
        self.assertEqual(self.user.profile.mfa_secret, secret)
        self.assertEqual(len(self.user.profile.mfa_recovery_codes), 8)
        for code in codes:
            self.assertNotIn(code, self.user.profile.mfa_recovery_codes)

    def test_invalid_totp_does_not_enable_mfa(self):
        secret = new_totp_secret()
        self.assertIsNone(enable_mfa(self.user.profile, secret, "000000"))
        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.profile.mfa_enabled)

    def test_recovery_code_is_single_use(self):
        secret = new_totp_secret()
        codes = enable_mfa(self.user.profile, secret, pyotp.TOTP(secret).now())
        self.assertTrue(consume_recovery_code(self.user.profile, codes[0]))
        self.assertFalse(consume_recovery_code(self.user.profile, codes[0]))
        self.user.profile.refresh_from_db()
        self.assertEqual(len(self.user.profile.mfa_recovery_codes), 7)

    def test_disable_mfa_clears_security_material(self):
        secret = new_totp_secret()
        enable_mfa(self.user.profile, secret, pyotp.TOTP(secret).now())
        disable_mfa(self.user.profile)
        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.profile.mfa_enabled)
        self.assertEqual(self.user.profile.mfa_secret, "")
        self.assertEqual(self.user.profile.mfa_recovery_codes, [])
        self.assertIsNone(self.user.profile.mfa_confirmed_at)


class MFAEnrollmentViewTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="MFA View Barn")
        self.user = User.objects.create_user(username="mfa-view", email="view@example.com", password="secure-test-password")
        self.user.profile.team = self.team
        self.user.profile.save(update_fields=["team"])
        self.client.force_login(self.user)

    def test_setup_requires_valid_code_and_shows_recovery_codes_once(self):
        response = self.client.get(reverse("mfa_setup"))
        self.assertEqual(response.status_code, 200)
        secret = self.client.session["mfa_enrollment_secret"]
        response = self.client.post(reverse("mfa_setup"), {"code": pyotp.TOTP(secret).now()})
        self.assertRedirects(response, reverse("mfa_recovery_codes"))
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.mfa_enabled)

        response = self.client.get(reverse("mfa_recovery_codes"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "These codes will not be shown again.")
        response = self.client.get(reverse("mfa_recovery_codes"))
        self.assertRedirects(response, reverse("my_account"))

    def test_disable_requires_current_password(self):
        secret = new_totp_secret()
        enable_mfa(self.user.profile, secret, pyotp.TOTP(secret).now())
        response = self.client.post(reverse("mfa_disable"), {"current_password": "wrong"})
        self.assertEqual(response.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.mfa_enabled)

        response = self.client.post(reverse("mfa_disable"), {"current_password": "secure-test-password"})
        self.assertRedirects(response, reverse("my_account"))
        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.profile.mfa_enabled)

    def test_my_account_exposes_mfa_state(self):
        response = self.client.get(reverse("my_account"))
        self.assertContains(response, "Set up MFA")
        secret = new_totp_secret()
        enable_mfa(self.user.profile, secret, pyotp.TOTP(secret).now())
        response = self.client.get(reverse("my_account"))
        self.assertContains(response, "Disable MFA")
