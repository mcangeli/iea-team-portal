import pyotp
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.mfa import enable_mfa
from portal.models import Team


class MFALoginTests(TestCase):
    password = "secure-test-password"

    def setUp(self):
        self.team = Team.objects.create(name="MFA Login Barn")
        self.user = User.objects.create_user(username="mfa-login", email="login@example.com", password=self.password)
        self.user.profile.team = self.team
        self.user.profile.must_change_password = False
        self.user.profile.save(update_fields=["team", "must_change_password"])

    def _enable_mfa(self):
        secret = pyotp.random_base32()
        codes = enable_mfa(self.user.profile, secret, pyotp.TOTP(secret).now())
        self.user.profile.refresh_from_db()
        return secret, codes

    def test_non_mfa_user_uses_normal_login(self):
        response = self.client.post(reverse("login"), {"username": self.user.username, "password": self.password})
        self.assertEqual(response.status_code, 302)
        self.assertNotEqual(response.url, reverse("mfa_login_challenge"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_mfa_user_is_not_authenticated_after_password(self):
        self._enable_mfa()
        response = self.client.post(reverse("login"), {"username": self.user.username, "password": self.password})
        self.assertRedirects(response, reverse("mfa_login_challenge"), fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(self.client.session["mfa_pending_user_id"], self.user.pk)

    def test_invalid_totp_does_not_authenticate(self):
        self._enable_mfa()
        self.client.post(reverse("login"), {"username": self.user.username, "password": self.password})
        response = self.client.post(reverse("mfa_login_challenge"), {"code": "000000"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertContains(response, "not valid")

    def test_valid_totp_completes_login(self):
        secret, _ = self._enable_mfa()
        self.client.post(reverse("login"), {"username": self.user.username, "password": self.password})
        response = self.client.post(reverse("mfa_login_challenge"), {"code": pyotp.TOTP(secret).now()})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)
        self.assertTrue(self.client.session["mfa_verified"])
        self.assertNotIn("mfa_pending_user_id", self.client.session)

    def test_recovery_code_completes_login_once(self):
        _, codes = self._enable_mfa()
        recovery_code = codes[0]
        self.client.post(reverse("login"), {"username": self.user.username, "password": self.password})
        response = self.client.post(reverse("mfa_login_challenge"), {"code": recovery_code})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

        self.client.logout()
        self.client.post(reverse("login"), {"username": self.user.username, "password": self.password})
        response = self.client.post(reverse("mfa_login_challenge"), {"code": recovery_code})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_next_destination_survives_mfa_challenge(self):
        secret, _ = self._enable_mfa()
        destination = reverse("my_account")
        response = self.client.post(
            f'{reverse("login")}?next={destination}',
            {"username": self.user.username, "password": self.password, "next": destination},
        )
        self.assertRedirects(response, reverse("mfa_login_challenge"), fetch_redirect_response=False)
        response = self.client.post(reverse("mfa_login_challenge"), {"code": pyotp.TOTP(secret).now()})
        self.assertRedirects(response, destination, fetch_redirect_response=False)

    def test_mfa_login_still_honors_forced_password_change(self):
        secret, _ = self._enable_mfa()
        self.user.profile.must_change_password = True
        self.user.profile.save(update_fields=["must_change_password"])
        self.client.post(reverse("login"), {"username": self.user.username, "password": self.password})
        response = self.client.post(reverse("mfa_login_challenge"), {"code": pyotp.TOTP(secret).now()})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

        response = self.client.get("/")
        self.assertRedirects(response, reverse("password_change_required"), fetch_redirect_response=False)

    def test_challenge_without_pending_password_auth_returns_to_login(self):
        response = self.client.get(reverse("mfa_login_challenge"))
        self.assertRedirects(response, reverse("login"), fetch_redirect_response=False)
