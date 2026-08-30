"""Data minimisation between the device and the model.

Rule of the project: the model receives *derived numbers*, never a raw activity
log. This module is the single chokepoint that builds that payload, and its
output is stored verbatim with every generated artifact so the user can audit
exactly what left their machine.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from .models import Metrics, Profile

# Free text is the highest-risk field: users paste names, workplaces, symptoms.
_REDACTIONS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "[email]"),
    (re.compile(r"https?://\S+"), "[link]"),
    (re.compile(r"(?<!\d)(\+?\d[\d\s().-]{8,}\d)(?!\d)"), "[phone]"),
    (re.compile(r"\b\d{11,}\b"), "[id]"),
    (re.compile(r"(?<!\w)@[A-Za-z0-9_]{3,}"), "[handle]"),
    (re.compile(r"\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b"), "[date]"),
]

MAX_CONTEXT_CHARS = 400


def redact(text: str) -> str:
    out = (text or "").strip()
    for pattern, replacement in _REDACTIONS:
        out = pattern.sub(replacement, out)
    if len(out) > MAX_CONTEXT_CHARS:
        out = out[:MAX_CONTEXT_CHARS] + " …"
    return out


def _pseudonymise_apps(top_apps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Category-only mode: 'Instagram' becomes 'social app A'."""
    counters: dict[str, int] = {}
    out = []
    for app in top_apps:
        cat = app.get("category", "other")
        counters[cat] = counters.get(cat, 0) + 1
        label = f"{cat} app {chr(64 + counters[cat])}"
        out.append({**app, "name": label})
    return out


def build_payload(metrics: Metrics, profile: Profile, checkins: list[dict],
                  week: dict | None = None) -> dict[str, Any]:
    """Assemble the minimised, redacted dict that is embedded in the prompt."""
    m = metrics.model_dump()
    top_apps = m["top_apps"] if profile.share_app_names else _pseudonymise_apps(m["top_apps"])
    longest_app = m["longest_session_app"] if profile.share_app_names else \
        f"{_category_of(m['top_apps'], m['longest_session_app'])} app"

    payload: dict[str, Any] = {
        "date": m["date_key"],
        "measured": {
            "total_minutes": m["total_minutes"],
            "by_category_minutes": m["by_category"],
            "top_apps": top_apps,
            "pickups": m["pickups"],
            "app_switches": m["switches"],
            "longest_unbroken_session_minutes": m["longest_session_minutes"],
            "longest_unbroken_session_app": longest_app,
            "late_night_minutes_23_to_05": m["late_night_minutes"],
            "first_use_local_time": m["first_use_local"],
            "last_use_local_time": m["last_use_local"],
            "longest_offline_block_minutes": m["longest_offline_block_minutes"],
            "busiest_hours": _busiest_hours(m["hourly_minutes"]),
        },
        "reliability": {
            "observed_span_hours": m["coverage_hours"],
            "days_of_history": m["days_of_history"],
            "baseline_daily_minutes": m["baseline_total_minutes"],
            "delta_vs_baseline_pct": m["delta_vs_baseline_pct"],
            "day_in_progress": _in_progress(m["date_key"]),
            "note": _reliability_note(m),
        },
        "user_goal": profile.goal,
        "self_reported_trigger": profile.trigger,
        "daily_target_minutes": profile.daily_target_minutes,
        "preferred_tone": profile.tone,
        "audience_flags": {
            # Coarse signal only -- never the exact age.
            "possible_minor": profile.age_band == "under_18",
        },
        "adherence_history": _adherence(checkins),
    }
    if profile.consent_context and profile.context.strip():
        payload["user_context_note"] = redact(profile.context)
    if week:
        payload["week_rollup"] = week
    return payload


def _category_of(top_apps: list[dict], name: str) -> str:
    for app in top_apps:
        if app.get("name") == name:
            return app.get("category", "other")
    return "other"


def _busiest_hours(hourly: list[int], top_n: int = 3) -> list[dict[str, int]]:
    ranked = sorted(range(24), key=lambda h: -hourly[h])[:top_n]
    return [{"hour": h, "minutes": hourly[h]} for h in ranked if hourly[h] > 0]


def _in_progress(date_key: str) -> bool:
    """A day that has not finished cannot be compared to finished days."""
    now = datetime.now()
    return date_key == now.strftime("%Y-%m-%d") and now.hour < 22


def _reliability_note(m: dict) -> str:
    if _in_progress(m["date_key"]):
        return ("This day is still in progress, so totals are partial and any comparison to a "
                "full-day baseline will look artificially low. Do not describe today as an "
                "improvement on that basis.")
    if m["total_minutes"] == 0:
        return "No usage was recorded for this date; treat every number as unknown."
    if m["coverage_hours"] < 3:
        return ("Only a short window of the day was observed, so totals are a floor, "
                "not a full picture.")
    if m["days_of_history"] < 3:
        return "Fewer than three days of history: comparisons to a baseline are not meaningful yet."
    return "Measurement window looks normal for this device."


def _adherence(checkins: list[dict]) -> dict[str, Any]:
    if not checkins:
        return {"entries": 0, "summary": "No check-ins yet -- this is the first plan."}
    counts: dict[str, int] = {}
    for c in checkins:
        counts[c["status"]] = counts.get(c["status"], 0) + 1
    recent = [{"date": c["date_key"], "action": c["action_id"], "status": c["status"],
               "note": redact(c.get("note", ""))[:120]} for c in checkins[:10]]
    return {"entries": len(checkins), "status_counts": counts, "recent": recent}
