from django.test import SimpleTestCase
from portal.templatetags.community_bbcode import render_community_bbcode


class CommunityBBCodeTests(SimpleTestCase):
    def test_basic_formatting(self):
        self.assertIn("<strong>Bold</strong>", render_community_bbcode("[b]Bold[/b]"))
        self.assertIn("<em>Italic</em>", render_community_bbcode("[i]Italic[/i]"))
        self.assertIn("<u>Underlined</u>", render_community_bbcode("[u]Underlined[/u]"))

    def test_raw_html_escaped(self):
        result = str(render_community_bbcode("<script>alert(1)</script>"))
        self.assertNotIn("<script>", result)
        self.assertIn("&lt;script&gt;", result)

    def test_rejects_javascript_url(self):
        result = str(render_community_bbcode("[url=javascript:alert(1)]click[/url]"))
        self.assertNotIn("<a ", result)

    def test_https_link_is_safe(self):
        result = str(render_community_bbcode("[url=https://example.org]Website[/url]"))
        self.assertIn('href="https://example.org"', result)
        self.assertIn("nofollow noopener noreferrer", result)

    def test_list(self):
        result = str(render_community_bbcode("[list][*]First[*]Second[/list]"))
        self.assertIn("<li>First</li>", result)
        self.assertIn("<li>Second</li>", result)
