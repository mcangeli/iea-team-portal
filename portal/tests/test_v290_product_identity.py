from django.test import TestCase
from django.urls import reverse

from portal.context_processors import PRODUCT_NAME, PRODUCT_TAGLINE


class ArenaLineProductIdentityTests(TestCase):
    def test_product_identity_constants(self):
        self.assertEqual(PRODUCT_NAME, "ArenaLine")
        self.assertEqual(PRODUCT_TAGLINE, "One team. One season. One place to manage it.")

    def test_login_page_uses_arenaline_identity(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign in · ArenaLine")
        self.assertContains(response, "WELCOME TO ARENALINE")
        self.assertContains(response, "Enter ArenaLine")
        self.assertContains(response, "One team. One season. One place to manage it.")
        self.assertContains(response, "/static/brand/arenaline-favicon.")
        self.assertContains(response, "/static/brand/arenaline-geometric-mark.")
        self.assertContains(response, "/static/css/arenaline-v290.")
        self.assertNotContains(response, "Team Portal")
