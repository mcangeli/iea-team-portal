from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class ArenaLinePreview4PeoplePresentationTests(SimpleTestCase):
    def _read(self, path):
        return (Path(settings.BASE_DIR) / path).read_text()

    def test_people_presentation_layer_is_loaded_by_shell(self):
        base = self._read("templates/base.html")
        css = self._read("static/css/people-v290.css")

        self.assertIn("css/people-v290.css", base)
        self.assertIn(".rider-card.club-rider-card", css)
        self.assertIn(".people-profile .profile", css)
        self.assertIn(".contact-card", css)
        self.assertIn(".people-form .form-section", css)

    def test_people_templates_opt_into_shared_people_surfaces(self):
        rider_list = self._read("templates/portal/rider_list.html")
        parent_list = self._read("templates/portal/parent_list.html")
        rider_detail = self._read("templates/portal/rider_detail.html")
        rider_form = self._read("templates/portal/rider_form.html")

        self.assertIn('class="people-roster"', rider_list)
        self.assertIn('class="people-directory"', parent_list)
        self.assertIn('class="people-profile"', rider_detail)
        self.assertIn('class="people-form"', rider_form)

    def test_people_presentation_preserves_iea_roster_semantics(self):
        rider_list = self._read("templates/portal/rider_list.html")
        rider_card = self._read("templates/portal/_rider_card.html")
        rider_detail = self._read("templates/portal/rider_detail.html")

        self.assertIn("Futures Team", rider_list)
        self.assertIn("Upper School Team", rider_list)
        self.assertIn("IEA · GRADES 4–8", rider_list)
        self.assertIn("IEA · GRADES 9–12", rider_list)
        self.assertIn("membership.get_team_level_display", rider_card)
        self.assertIn("IEA member", rider_detail)

    def test_rider_profile_privacy_boundary_remains_visible_in_template(self):
        rider_detail = self._read("templates/portal/rider_detail.html")

        self.assertIn("{% if private_view %}", rider_detail)
        self.assertIn("Personal contact and family information is private.", rider_detail)
        self.assertIn("{% if can_manage or family_account_membership %}", rider_detail)
        self.assertIn("{% if private_view and active_season %}", rider_detail)
