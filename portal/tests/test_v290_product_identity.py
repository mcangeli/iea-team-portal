from pathlib import Path

from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from portal.context_processors import (
    ARENA_MODULES,
    DEFAULT_ENABLED_MODULES,
    PRODUCT_NAME,
    PRODUCT_TAGLINE,
)


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

    def test_brand_styles_keep_light_and_dark_modes(self):
        css = (Path(settings.BASE_DIR) / "static/css/arenaline-v290.css").read_text()
        self.assertIn('html[data-theme="light"]', css)
        self.assertIn('html[data-theme="dark"]', css)
        self.assertIn("--arena-navy:#0E2A47", css)
        self.assertIn("--arena-gold:#C9A96B", css)
        self.assertIn("--arena-blue:#007297", css)

    def test_primary_surfaces_use_arenaline_language(self):
        templates = Path(settings.BASE_DIR) / "templates/portal"
        dashboard = (templates / "dashboard.html").read_text()
        my_team = (templates / "my_team.html").read_text()
        show_manager = (templates / "dashboard_show_manager.html").read_text()

        self.assertIn("Dashboard · ArenaLine", dashboard)
        self.assertIn("ARENALINE · SEASON HOME", dashboard)
        self.assertNotIn("Equestrian Team Portal", dashboard)
        self.assertIn("My Team · ArenaLine", my_team)
        self.assertIn("ARENALINE · TEAM HUB", my_team)
        self.assertIn("Show Manager · ArenaLine", show_manager)
        self.assertIn("ARENALINE · SHOW HOST OPERATIONS", show_manager)

    def test_shell_exposes_arenaline_domain_navigation(self):
        base = (Path(settings.BASE_DIR) / "templates/base.html").read_text()

        for module_id in (
            'data-module="core"',
            'data-module="people"',
            'data-module="horses"',
            'data-module="competition_iea"',
            'data-module="operations"',
            'data-module="finance"',
            'data-module="communications"',
        ):
            self.assertIn(module_id, base)

        self.assertIn("People & families", base)
        self.assertIn("Horse management", base)
        self.assertIn("IEA competition", base)
        self.assertIn("Everyday operations", base)
        self.assertIn("Organization administration", base)
        self.assertIn("ArenaLine' }} · Equestrian operations", base)

    def test_module_registry_separates_platform_from_iea_competition(self):
        self.assertEqual(set(DEFAULT_ENABLED_MODULES), set(ARENA_MODULES))
        self.assertEqual(ARENA_MODULES["competition_iea"]["scope"], "competition")
        for module_id in ("core", "people", "horses", "operations", "finance", "communications"):
            self.assertEqual(ARENA_MODULES[module_id]["scope"], "platform")

    def test_context_exposes_module_metadata_for_future_enablement(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.context["portal_modules"], ARENA_MODULES)
        self.assertEqual(tuple(response.context["portal_enabled_modules"]), DEFAULT_ENABLED_MODULES)
        self.assertEqual(response.context["portal_organization_label"], "Organization")

    def test_platform_surfaces_use_generic_language_but_keep_iea_specialization(self):
        templates = Path(settings.BASE_DIR) / "templates/portal"
        horses = (templates / "horse_list.html").read_text()
        riders = (templates / "rider_list.html").read_text()
        finance = (templates / "finance_dashboard.html").read_text()

        self.assertIn("Horse Registry · ArenaLine", horses)
        self.assertIn("ARENALINE · HORSE MANAGEMENT", horses)
        self.assertNotIn("Team Portal", horses)
        self.assertIn("Riders · ArenaLine", riders)
        self.assertIn("ARENALINE · PEOPLE", riders)
        self.assertIn("IEA · GRADES 4–8", riders)
        self.assertIn("IEA · GRADES 9–12", riders)
        self.assertIn("Finance · ArenaLine", finance)
        self.assertIn("ARENALINE · FINANCE", finance)
        self.assertIn("organization’s", finance)

    def test_preview_2c_generic_surface_sweep_and_domain_boundaries(self):
        templates = Path(settings.BASE_DIR) / "templates/portal"

        parent_list = (templates / "parent_list.html").read_text()
        former_riders = (templates / "former_rider_list.html").read_text()
        action_items = (templates / "action_item_list.html").read_text()
        volunteer = (templates / "volunteer_dashboard.html").read_text()
        calendar = (templates / "calendar.html").read_text()
        notifications = (templates / "notifications.html").read_text()
        users = (templates / "user_list.html").read_text()
        committees = (templates / "committee_list.html").read_text()
        season_setup = (templates / "season_setup.html").read_text()
        generic_form = (templates / "form.html").read_text()
        confirm_delete = (templates / "confirm_delete.html").read_text()

        self.assertIn("Parents & Guardians · ArenaLine", parent_list)
        self.assertIn("ARENALINE · PEOPLE", parent_list)
        self.assertIn("Futures", parent_list)
        self.assertIn("Upper School", parent_list)

        self.assertIn("Alumni / Former Riders · ArenaLine", former_riders)
        self.assertIn("ARENALINE · PEOPLE", former_riders)
        self.assertIn("current organization operations", former_riders)

        self.assertIn("Action Items · ArenaLine", action_items)
        self.assertIn("ARENALINE · OPERATIONS", action_items)
        self.assertIn("organization needs to get done", action_items)
        self.assertNotIn("TEAM HUB", action_items)

        self.assertIn("Volunteer Hours · ArenaLine", volunteer)
        self.assertIn("ARENALINE · OPERATIONS", volunteer)
        self.assertNotIn("awaiting coach approval", volunteer)

        self.assertIn("Calendar · ArenaLine", calendar)
        self.assertIn("ARENALINE · OPERATIONS", calendar)
        self.assertIn("organization events", calendar)
        self.assertNotIn("Team calendar", calendar)

        self.assertIn("Notifications · ArenaLine", notifications)
        self.assertIn("ARENALINE · COMMUNICATIONS", notifications)
        self.assertIn("organization updates", notifications)

        self.assertIn("Users · ArenaLine", users)
        self.assertIn("ARENALINE · ADMINISTRATION", users)
        self.assertIn("Committees · ArenaLine", committees)
        self.assertIn("ARENALINE · ADMINISTRATION", committees)
        self.assertIn("Season Setup · ArenaLine", season_setup)

        self.assertIn("{{ title }} · ArenaLine", generic_form)
        self.assertIn('default:"ARENALINE"', generic_form)
        self.assertIn("{{ title }} · ArenaLine", confirm_delete)

        # IEA-specific competition and program terminology remains deliberately intact.
        self.assertIn("Futures Team", season_setup)
        self.assertIn("Upper School Team", season_setup)
        self.assertIn("HORSE &amp; HOOFPRINT MANAGEMENT", season_setup)
        self.assertIn("Regionals", season_setup)
        self.assertIn("Zones", season_setup)
        self.assertIn("Nationals", season_setup)
