from django.test import TestCase
from django.urls import reverse

from portal.context_processors import PRODUCT_NAME, PRODUCT_TAGLINE


class ArenaLineProductIdentityTests(TestCase):
    def test_product_identity_constants(self):
        self.assertEqual(PRODUCT_NAME, "ArenaLine")
        self.assertIn("Equestrian operations", PRODUCT_TAGLINE)

    def test_login_page_uses_arenaline_identity(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign in · ArenaLine")
        self.assertContains(response, "WELCOME TO ARENALINE")
        self.assertContains(response, "Enter ArenaLine")
        self.assertNotContains(response, "Team Portal")
