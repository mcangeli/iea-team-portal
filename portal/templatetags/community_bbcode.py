"""Conservative BBCode renderer for user-authored Community posts.

Input is always HTML-escaped first. Only a small allowlist of BBCode is
translated into HTML; raw HTML and unsafe URL schemes never become active.
"""
import re
from html import escape
from urllib.parse import urlsplit

from django import template
from django.utils.safestring import mark_safe

register = template.Library()
_PAIR = {"b": "strong", "i": "em", "u": "u", "s": "s", "quote": "blockquote", "code": "code"}
_TAG = re.compile(r"\[(/?)(b|i|u|s|quote|code)\]", re.I)
_URL = re.compile(r"\[url(?:=([^\]\r\n]+))?\](.*?)\[/url\]", re.I | re.S)
_LIST = re.compile(r"\[list\](.*?)\[/list\]", re.I | re.S)
_ITEM = re.compile(r"\[\*\](.*?)(?=\[\*\]|$)", re.I | re.S)


def _safe_url(raw):
    url = raw.strip()
    try:
        parsed = urlsplit(url)
    except ValueError:
        return None
    if parsed.scheme.lower() not in {"https", "http"} or not parsed.netloc:
        return None
    if any(ord(ch) < 33 or ord(ch) == 127 for ch in url):
        return None
    return url


def render_community_bbcode(value):
    source = str(value or "")
    # Build markup from escaped text only, never trust author HTML.
    result = []
    position = 0
    stack = []
    for match in _TAG.finditer(source):
        result.append(escape(source[position:match.start()]))
        closing, name = match.group(1), match.group(2).lower()
        if closing:
            if stack and stack[-1] == name:
                stack.pop()
                result.append(f"</{_PAIR[name]}>")
            else:
                result.append(escape(match.group(0)))
        else:
            stack.append(name)
            result.append(f"<{_PAIR[name]}>")
        position = match.end()
    result.append(escape(source[position:]))
    while stack:
        result.append(f"</{_PAIR[stack.pop()]}>")
    html = "".join(result)

    def replace_url(match):
        raw = match.group(1) if match.group(1) is not None else match.group(2)
        from html import unescape
        url = _safe_url(unescape(raw))
        if not url:
            return match.group(0)
        return f'<a href="{escape(url, quote=True)}" rel="nofollow noopener noreferrer" target="_blank">{match.group(2)}</a>'

    html = _URL.sub(replace_url, html)

    def replace_list(match):
        items = _ITEM.findall(match.group(1))
        return "<ul>" + "".join(f"<li>{item.strip()}</li>" for item in items) + "</ul>" if items else match.group(0)

    html = _LIST.sub(replace_list, html)
    return mark_safe(html.replace("\n", "<br>"))


register.filter("community_bbcode", render_community_bbcode)
