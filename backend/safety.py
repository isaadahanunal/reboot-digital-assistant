"""Guardrails around the generative layer.

Two independent gates, because prompt instructions alone are not a safety
control -- a model can ignore them, and a hackathon judge should see a
deterministic backstop:

  * ``screen_input``  runs BEFORE any API call. If the user's free text signals
    acute distress, we do not ask an LLM to "coach" them; we return signposting
    to human help and skip generation entirely.
  * ``screen_output`` runs AFTER generation. It looks for clinical language,
    absolute promises and judgemental framing, and annotates or rewrites them.
"""
from __future__ import annotations

import re
from typing import Any

DISCLAIMER = (
    "Reboot is a self-guided digital habit tool. It is not a medical device and "
    "does not diagnose or treat any condition. If screen use is affecting your "
    "sleep, mood, studies or relationships, please talk to a qualified professional."
)

# Deliberately broad, bilingual (EN/TR) and biased towards false positives:
# a wrongly shown help card costs nothing, a missed one can cost a lot.
_CRISIS = re.compile(
    r"\b(suicid|kill myself|end my life|self[- ]harm|cutting myself|want to die|"
    r"hopeless|worthless|can'?t go on|panic attack|starving myself|"
    r"intihar|kendime zarar|ya[sş]amak istemiyorum|de[gğ]ersizim|umutsuz|"
    r"panik ata[kğ]|bunal[iı]m)\b", re.I)

# Clinical vocabulary comes in two flavours and they need different matching.
# Words are matched case-insensitively. Acronyms must NOT be: an earlier version
# listed "ADD" alongside the words, and case-insensitive matching turned every
# ordinary "add" into a clinical-language flag -- so "Add a tiny bit of friction"
# was rewritten to "screen-use habit a tiny bit of friction" and the reply was
# labelled as guardrail-adjusted. A safety badge that fires on good output stops
# meaning anything, which is worse than not having one.
_CLINICAL_WORDS = re.compile(
    r"\b(addicted|addiction|dependency|disorder|depress\w*|anxiety disorder|"
    r"diagnos\w*|clinical\w*|symptom|patholog\w*|dopamine detox|withdrawal|"
    r"ba[gğ][iı]ml[iı]l[iı]k|te[sş]his|bozuklu[gğ]u|depresyon)\b", re.I)
_CLINICAL_ACRONYMS = re.compile(r"\b(ADHD|ADD|OCD|PTSD|OKB|DEHB)\b")   # case-sensitive on purpose


class _Clinical:
    """Presents the two patterns as one object so callers stay unchanged."""

    def search(self, text: str):
        return _CLINICAL_WORDS.search(text) or _CLINICAL_ACRONYMS.search(text)

    def sub(self, replacement: str, text: str) -> str:
        return _CLINICAL_ACRONYMS.sub(replacement, _CLINICAL_WORDS.sub(replacement, text))


_CLINICAL = _Clinical()

_ABSOLUTE = re.compile(
    r"\b(guarantee\w*|will definitely|always works|cure[sd]?|proven to|100%|"
    r"kesinlikle iyile[sş]|garanti)\b", re.I)

_JUDGEMENT = re.compile(
    r"\b(lazy|pathetic|wasting your life|shameful|disgusting|you should be ashamed|"
    r"no self[- ]control|weak[- ]willed|tembel|utan[cç])\b", re.I)

SUPPORT_CARD = {
    "title": "Let's pause the coaching for a moment",
    "body": (
        "Some of what you wrote sounds heavier than screen-time habits, and an "
        "automated coach is the wrong tool for that. You deserve a person, not an "
        "algorithm. Please consider reaching out to someone you trust, a campus "
        "counsellor, or a local support line."
    ),
    "resources": [
        {"region": "Türkiye", "name": "ALO 183 Sosyal Destek Hattı", "contact": "183"},
        {"region": "Türkiye", "name": "Acil / Emergency", "contact": "112"},
        {"region": "International", "name": "Find a helpline", "contact": "https://findahelpline.com"},
    ],
    "note": "Your usage data was not sent anywhere. You can still use the offline dashboard.",
}


def screen_input(*texts: str) -> dict[str, Any]:
    joined = " ".join(t or "" for t in texts)
    if _CRISIS.search(joined):
        return {"risk": "high", "block_generation": True, "card": SUPPORT_CARD}
    return {"risk": "none", "block_generation": False, "card": None}


def _walk_strings(obj: Any, fn):
    if isinstance(obj, str):
        return fn(obj)
    if isinstance(obj, list):
        return [_walk_strings(v, fn) for v in obj]
    if isinstance(obj, dict):
        return {k: _walk_strings(v, fn) for k, v in obj.items()}
    return obj


def screen_output(payload: dict) -> tuple[dict, list[str]]:
    """Detect-only pass. Returns (payload unchanged, guardrail flags).

    Detection is separated from repair on purpose: silently rewriting the model's
    words produces mangled sentences and hides the failure. Flagged output is
    sent back to the model for a targeted revision (see ``prompts.REVISION_*``),
    and only if that also fails do we fall back to ``neutralize``.
    """
    flags: list[str] = []

    def check(text: str) -> str:
        for label, pattern in (("clinical_language", _CLINICAL),
                               ("overclaim", _ABSOLUTE),
                               ("judgemental", _JUDGEMENT)):
            hit = pattern.search(text)
            if hit:
                flags.append(f"{label}: {hit.group(0)}")
        return text

    _walk_strings(payload, check)
    return payload, sorted(set(flags))


def neutralize(payload: dict) -> dict:
    """Last-resort scrub used only when a revision pass still trips a guardrail."""

    def scrub(text: str) -> str:
        out = _ABSOLUTE.sub("can help some people", text)
        out = _CLINICAL.sub("screen-use habit", out)
        out = _JUDGEMENT.sub("", out)
        return re.sub(r"\s{2,}", " ", out).strip()

    return _walk_strings(payload, scrub)


def confidence_for(metrics_payload: dict) -> str:
    """Honest uncertainty label, derived from measurement quality, not from the model."""
    rel = metrics_payload.get("reliability", {})
    if metrics_payload.get("measured", {}).get("total_minutes", 0) == 0:
        return "none"
    if rel.get("observed_span_hours", 0) < 3:
        return "low"
    if rel.get("days_of_history", 0) < 3 or rel.get("day_in_progress"):
        return "medium"
    return "high"
