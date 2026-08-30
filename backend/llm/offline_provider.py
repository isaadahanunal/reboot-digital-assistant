"""Deterministic fallback coach -- no network, no model, no API key.

Why this exists, beyond convenience: a well-being tool that shows a blank screen
when a quota runs out is worse than one that degrades. It is also an honesty
device. Its output is labelled "rule-based, not AI-generated" everywhere in the
UI, so nobody can mistake template text for model reasoning, and it gives a
concrete baseline to compare the generated digests against.
"""
from __future__ import annotations

from typing import Any

from ..taxonomy import DISCRETIONARY
from .base import ProviderError

_CATEGORY_LABEL = {
    "social": "social apps", "entertainment": "video and music",
    "communication": "messaging", "work": "work and study tools",
    "reading": "reading", "games": "games", "shopping": "shopping",
    "utility": "system utilities", "other": "other apps",
}


def _hm(minutes: int) -> str:
    h, m = divmod(max(0, int(minutes)), 60)
    return f"{h}h {m:02d}m" if h else f"{m}m"


class OfflineProvider:
    name = "offline"
    model = "rule-based-v1"

    def generate_json(self, system: str, user: str, schema: dict[str, Any],
                      context: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = context or {}
        kind = payload.get("_kind", "daily_digest")
        return (weekly_plan(payload) if kind == "weekly_plan" else daily_digest(payload))

    def generate_text(self, system: str, messages: list[dict[str, str]]) -> str:
        """The offline coach cannot hold a conversation, and pretending otherwise
        with canned replies would be the dishonest option. It says so instead."""
        raise ProviderError(
            "The offline coach can write digests and plans from templates, but it cannot hold a "
            "conversation — that needs a language model. Turn the AI coach on in Settings, or keep "
            "using the Today and Plan tabs.", kind="offline_chat")


def _facts(payload: dict) -> dict:
    m = payload.get("measured", {})
    rel = payload.get("reliability", {})
    cats = m.get("by_category_minutes", {}) or {}
    disc = sum(v for k, v in cats.items() if k in DISCRETIONARY)
    top_cat = max(cats, key=cats.get) if cats else "other"
    apps = m.get("top_apps", []) or []
    return {
        "m": m, "rel": rel, "cats": cats, "disc": disc, "top_cat": top_cat,
        "top_app": apps[0]["name"] if apps else "your busiest app",
        "total": m.get("total_minutes", 0),
        "late": m.get("late_night_minutes_23_to_05", 0),
        "longest": m.get("longest_unbroken_session_minutes", 0),
        "pickups": m.get("pickups", 0),
        "peak": (m.get("busiest_hours") or [{"hour": 21}])[0]["hour"],
        "goal": payload.get("user_goal", "a calmer relationship with your phone"),
        "trigger": payload.get("self_reported_trigger", "your usual trigger moment"),
    }


def daily_digest(payload: dict) -> dict:
    f = _facts(payload)
    total, late, longest, pickups, peak = f["total"], f["late"], f["longest"], f["pickups"], f["peak"]
    delta = f["rel"].get("delta_vs_baseline_pct", 0)
    history = f["rel"].get("days_of_history", 0)

    if total == 0:
        return _empty_digest()

    observations = [
        {"metric": "Total measured time",
         "value": _hm(total),
         "reading": (f"About {_hm(f['disc'])} of that sat in discretionary categories "
                     f"({', '.join(_CATEGORY_LABEL.get(c, c) for c in list(f['cats'])[:2])}).")},
        {"metric": "Longest unbroken session",
         "value": _hm(longest),
         "reading": (f"Sessions past ~25 minutes are usually where a check-in turns into a stay. "
                     f"Today's longest was in {f['m'].get('longest_unbroken_session_app', 'one app')}.")},
    ]
    if late > 0:
        observations.append({
            "metric": "Late-night use (23:00-05:00)", "value": _hm(late),
            "reading": "Screen time in this window is the piece most often linked to how the next morning feels."})
    else:
        observations.append({
            "metric": "Pickups", "value": str(pickups),
            "reading": f"Your busiest hour was around {peak:02d}:00, which is where a boundary would bite hardest."})

    experiments = _experiments(f)
    well = ("Your longest offline block today was "
            f"{_hm(f['m'].get('longest_offline_block_minutes', 0))} — that is the habit to copy, not fix.")
    if history >= 3 and delta < 0 and not f["rel"].get("day_in_progress"):
        well = f"Today ran {abs(delta)}% below your 7-day average. Worth noticing what was different."

    return {
        "headline": f"{_hm(total)} on screen, peak around {peak:02d}:00",
        "summary": (f"You logged {_hm(total)} of measured foreground time across {pickups} pickups, "
                    f"with {_CATEGORY_LABEL.get(f['top_cat'], f['top_cat'])} leading the day. "
                    + ("The day is not over yet, so this is a partial total and not comparable to a full-day average."
                       if f["rel"].get("day_in_progress") else
                       f"That is {abs(delta)}% {'below' if delta < 0 else 'above'} your recent average."
                       if history >= 3 else "There is not enough history yet to compare this to a baseline.")),
        "observations": observations[:3],
        "what_went_well": well,
        "pattern_hypothesis": (f"One possibility: the moment you described — {f['trigger'].lower()} — lines up with "
                               f"the {peak:02d}:00 peak. You would know better than the log whether that is what happened."),
        "confidence": _confidence(f["rel"], total),
        "micro_experiments": experiments,
        "boundary_suggestion": _boundary(f),
        "user_check_question": "Which of today's stretches felt like a choice, and which one felt automatic?",
        "data_i_could_not_see": ("This log only sees foreground app time on connected devices. It cannot see "
                                 "what you were doing, why, whether the time was worth it, or any use on "
                                 "devices you have not connected."),
    }


def _confidence(rel: dict, total: int) -> str:
    if total == 0:
        return "low"
    if rel.get("observed_span_hours", 0) < 3:
        return "low"
    if rel.get("days_of_history", 0) < 3 or rel.get("day_in_progress"):
        return "medium"
    return "high"


def _experiments(f: dict) -> list[dict]:
    out: list[dict] = []
    peak, late, longest = f["peak"], f["late"], f["longest"]
    if late > 10:
        out.append({
            "id": "night-charger",
            "title": "Charge the phone outside the bedroom tonight",
            "if_then": "If I get into bed and reach for my phone, then I pick up whatever is on the nightstand instead.",
            "effort_minutes": 3,
            "why_this": (f"You logged {_hm(late)} after 23:00. Moving the charger changes the environment once, "
                         "instead of asking for a decision every night. Smaller version: face-down, arm's length away."),
        })
    if longest >= 25:
        out.append({
            "id": "session-timer",
            "title": f"Put a 15-minute timer on {f['top_app']} before you open it",
            "if_then": f"If I unlock to open {f['top_app']}, then I start a 15-minute timer first.",
            "effort_minutes": 2,
            "why_this": (f"Your longest unbroken stretch was {_hm(longest)}. The timer does not stop you; it just "
                         "makes the moment of continuing a conscious one. Smaller version: say the time out loud."),
        })
    out.append({
        "id": "peak-swap",
        "title": f"Pre-decide one alternative for {peak:02d}:00",
        "if_then": f"If it is around {peak:02d}:00 and I reach for my phone out of habit, then I do the alternative I picked this morning.",
        "effort_minutes": 5,
        "why_this": ("A replacement chosen in advance beats one improvised in the moment. Pick something that takes "
                     "under two minutes to start. Smaller version: just name it, do not commit to it."),
    })
    return out[:3]


def _boundary(f: dict) -> dict:
    if f["late"] > 10:
        return {"rule": "No phone in the bedroom after 23:30.",
                "how_to_set_it": ("Set a Bedtime/Focus schedule at 23:15 that allows only calls from favourites, "
                                  "and move the charger out of arm's reach from the bed.")}
    return {"rule": f"One screen-free hour around {f['peak']:02d}:00 on weekdays.",
            "how_to_set_it": ("Use your phone's Focus/Digital Wellbeing schedule for that hour, allow calls through, "
                              "and put the phone somewhere that needs standing up to reach.")}


def _empty_digest() -> dict:
    return {
        "headline": "No usage recorded for this day",
        "summary": ("Nothing was logged for this date, so there is nothing to interpret. Either the device agent "
                    "was not running, or this device was not in use."),
        "observations": [
            {"metric": "Total measured time", "value": "0m", "reading": "No foreground activity reached the local database."},
            {"metric": "Coverage", "value": "0h", "reading": "Start the device agent, import an export, or load the demo day."},
        ],
        "what_went_well": "Nothing to grade today — an empty log is not an achievement or a failure.",
        "pattern_hypothesis": "No data, so no hypothesis. Guessing here would be inventing.",
        "confidence": "low",
        "micro_experiments": [
            {"id": "connect", "title": "Connect a device source", "effort_minutes": 2,
             "if_then": "If I want a real digest, then I start the device agent before I begin my day.",
             "why_this": "A coach with no measurements can only produce generic advice, which is what you already have."},
            {"id": "baseline", "title": "Collect two ordinary days first", "effort_minutes": 0,
             "if_then": "If I have not measured a normal week yet, then I change nothing and just observe.",
             "why_this": "Changing behaviour before you have a baseline makes it impossible to tell whether it worked."},
        ],
        "boundary_suggestion": {"rule": "None yet.",
                                "how_to_set_it": "Boundaries set without data tend to be arbitrary. Measure first."},
        "user_check_question": "Was this a day away from your devices, or was the agent simply not running?",
        "data_i_could_not_see": "Everything — there are no measurements for this date.",
    }


_LADDER = [
    ("Mon", "Observe only", "Write down the time of your first pickup and your last one. Change nothing else.",
     "If I notice myself scrolling, then I note the time and carry on.", 2,
     "Too much? Just note the last pickup of the day."),
    ("Tue", "Environment, not willpower", "Move your three most-opened apps off the home screen into a folder on page 2.",
     "If I unlock and my thumb goes to where the app used to be, then I let the pause happen and decide again.", 4,
     "Too much? Move just one app."),
    ("Wed", "Protect the peak hour", "Schedule a Focus/Do Not Disturb block over your busiest hour, allowing calls through.",
     "If the Focus block starts and I want to override it, then I wait until it ends before deciding.", 5,
     "Too much? Make the block 20 minutes instead of an hour."),
    ("Thu", "One substitution", "Choose one specific replacement activity and leave it physically visible.",
     "If I reach for my phone during my trigger moment, then I do the replacement for two minutes first.", 5,
     "Too much? Two minutes of standing up counts."),
    ("Fri", "Boundary at night", "Charge the phone outside the bedroom, or across the room from the bed.",
     "If I am in bed and reach for the phone, then I read one page instead.", 3,
     "Too much? Face-down and out of arm's reach."),
    ("Sat", "Deliberately easy day", "No restrictions. Use your phone however you like and notice how it feels.",
     "If I feel guilty about today, then I remind myself that a rest day is part of the plan.", 0,
     "Nothing to scale down — that is the point."),
    ("Sun", "Review and choose one keeper", "Pick the single change from this week that cost the least and kept the most.",
     "If I can only keep one habit next week, then it is that one.", 10,
     "Too much? Just name the keeper out loud."),
]


def weekly_plan(payload: dict) -> dict:
    f = _facts(payload)
    baseline = f["rel"].get("baseline_daily_minutes", 0) or f["total"]
    history = f["rel"].get("days_of_history", 0)
    observation_only = baseline == 0 or history < 3
    target_to = max(60, int(baseline * 0.85)) if not observation_only else 0

    days = [{"id": f"d{i+1}-{d[0].lower()}", "day": d[0], "focus": d[1], "action": d[2],
             "if_then": d[3], "effort_minutes": d[4], "fallback": d[5]}
            for i, d in enumerate(_LADDER)]
    if f["late"] > 10:
        days[4]["focus"] = f"Protect the late window (you logged {_hm(f['late'])} after 23:00)"

    adherence = payload.get("adherence_history", {})
    counts = adherence.get("status_counts", {}) if isinstance(adherence, dict) else {}
    hard = counts.get("skipped", 0) + counts.get("too_hard", 0)
    note = "First plan — nothing to adapt from yet."
    if hard >= 2:
        for day in days:
            day["effort_minutes"] = max(0, day["effort_minutes"] // 2)
        days[3] = {**days[3], "focus": "Observation only (eased)",
                   "action": "Skip the substitution this week. Just note when the urge shows up.",
                   "if_then": "If the urge shows up, then I note the time and do nothing about it.",
                   "effort_minutes": 1, "fallback": "Nothing to scale down."}
        note = (f"{hard} actions were skipped or marked too hard, so this week is lighter: effort halved and "
                "Thursday reduced to observation.")
    elif counts.get("done", 0) >= 4:
        note = "Most actions landed last week, so difficulty stays where it is and only the variety changes."

    return {
        "plan_title": f"Seven days around {f['goal'].lower()}",
        "north_star": (f"Spend less of your evening on autopilot, without banning anything. "
                       f"Anchor: your peak hour is around {f['peak']:02d}:00."),
        "weekly_target": {
            "metric": "observation only" if observation_only else "average daily screen minutes",
            "from_value": "unknown" if observation_only else f"{baseline} min",
            "to_value": "unknown" if observation_only else f"{target_to} min",
            "rationale": ("Fewer than three measured days, so any numeric target would be arbitrary. This week is "
                          "for measuring." if observation_only else
                          "A ~15% shift is small enough to survive a bad day and large enough to notice."),
        },
        "days": days,
        "environment_changes": [
            "Move the most-opened app off the home screen.",
            "Charge the phone outside arm's reach of the bed.",
            "Turn off notification badges for one discretionary app.",
        ],
        "guardrails": [
            "A missed day is data, not failure. Note what got in the way and continue.",
            "If any action increases anxiety rather than reducing it, drop it. This tool is not worth feeling worse over.",
            "This is general habit guidance, not treatment. If screen use is tangled up with sleep, mood or study problems, talk to a person.",
        ],
        "adaptation_note": note,
        "review_question": "Which single day this week was easiest to actually do, and what made it easy?",
    }
