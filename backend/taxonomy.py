"""App / domain -> category mapping.

Categorisation happens on the device, before anything is aggregated, so that a
"category only" privacy mode can drop raw app names entirely and still produce a
useful digest. The table is deliberately editable: a coach that mislabels your
work tool as "entertainment" gives biased advice, so users can correct it.
"""
from __future__ import annotations

import re

_RULES: list[tuple[str, str]] = [
    # (regex over lowercased app-or-domain, category)
    (r"instagram|tiktok|twitter|^x$|x corp|threads|facebook|snapchat|reddit|linkedin|bluesky|mastodon|pinterest|tumblr", "social"),
    (r"youtube|netflix|disney|prime video|spotify|twitch|hulu|blutv|exxen|vlc|quicktime|music|podcast|apple tv", "entertainment"),
    (r"whatsapp|telegram|signal|messenger|messages|discord|slack|teams|zoom|meet|skype|mail|outlook|gmail|thunderbird", "communication"),
    (r"code|xcode|terminal|iterm|pycharm|intellij|android studio|vim|emacs|docker|postman|figma|notion|obsidian|word|excel|powerpoint|pages|numbers|keynote|jira|confluence|github|gitlab|sublime|jupyter|matlab|blender|photoshop", "work"),
    (r"kindle|books|medium|pocket|substack|news|nytimes|bbc|guardian|arxiv|wikipedia", "reading"),
    (r"steam|epic games|minecraft|roblox|league of legends|valorant|fortnite|game|playstation|xbox", "games"),
    (r"amazon|trendyol|hepsiburada|ebay|aliexpress|shop|etsy|getir|yemeksepeti", "shopping"),
    (r"finder|explorer|settings|system preferences|system settings|calculator|calendar|clock|files|1password|keychain|activity monitor", "utility"),
    (r"chrome|safari|firefox|edge|arc|brave|opera", "other"),  # browsers resolved by domain when available
]

_BROWSERS = re.compile(r"chrome|safari|firefox|edge|arc|brave|opera", re.I)


def categorize(app: str, domain: str | None = None) -> str:
    """Return a category. Domain wins for browsers, because 'Chrome' is not a habit."""
    if domain and _BROWSERS.search(app or ""):
        cat = _match(domain)
        if cat != "other":
            return cat
        return "reading" if _looks_like_article(domain) else "other"
    return _match(app or "")


def _match(text: str) -> str:
    low = (text or "").lower()
    for pattern, category in _RULES:
        if re.search(pattern, low):
            return category
    return "other"


def _looks_like_article(domain: str) -> bool:
    return bool(re.search(r"blog|docs|wiki|news|dergi|haber", domain, re.I))


# Categories that most users describe as "the scroll" -- used only for a
# heuristic headline number, never as a moral judgement in the UI copy.
DISCRETIONARY = {"social", "entertainment", "games", "shopping"}
