from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class ArenaLinePreview4HorsePresentationTests(SimpleTestCase):
    def test_shared_horse_presentation_is_loaded(self):
        base = (Path(settings.BASE_DIR) / "templates/base.html").read_text()
        css = (Path(settings.BASE_DIR) / "static/css/horses-v290.css").read_text()

        self.assertIn("css/horses-v290.css", base)
        self.assertIn(".horse-card", css)
        self.assertIn(".horse-detail-grid>.card", css)
        self.assertIn(".horse-form-card", css)
        self.assertIn(".horse-readiness-badge", css)
        self.assertIn(".show-horse-card", css)

    def test_horse_templates_keep_shared_semantic_hooks(self):
        template_dir = Path(settings.BASE_DIR) / "templates/portal"
        horse_list = (template_dir / "horse_list.html").read_text()
        horse_detail = (template_dir / "horse_detail.html").read_text()
        horse_form = (template_dir / "horse_form.html").read_text()
        show_horses = (template_dir / "show_horses.html").read_text()
        readiness = (template_dir / "show_readiness.html").read_text()

        self.assertIn('class="card horse-card"', horse_list)
        self.assertIn('class="detail-grid horse-detail-grid"', horse_detail)
        self.assertIn('class="card form-card horse-form-card"', horse_form)
        self.assertIn('class="card horse-card show-horse-card"', show_horses)
        self.assertIn("horse-readiness-badge", readiness)

    def test_horse_presentation_preserves_iea_hoofprint_language(self):
        template_dir = Path(settings.BASE_DIR) / "templates/portal"
        horse_detail = (template_dir / "horse_detail.html").read_text()
        show_horses = (template_dir / "show_horses.html").read_text()
        readiness = (template_dir / "show_readiness.html").read_text()

        self.assertIn("HORSE &amp; HOOFPRINT MANAGEMENT", horse_detail)
        self.assertIn("Hoofprint Builder", show_horses)
        self.assertIn("Hoofprint Builder", readiness)
        self.assertIn("Coggins", horse_detail)
        self.assertIn("Season eligibility", horse_detail)
