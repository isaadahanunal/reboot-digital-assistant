"""Turn raw foreground sessions into the deterministic feature set the coach sees.

Every number the LLM is allowed to talk about is computed here, in plain Python.
The model does interpretation and planning; it never does arithmetic on raw logs.
That split is what keeps the digest from inventing statistics.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from . import store
from .models import Metrics
from .taxonomy import DISCRETIONARY

LATE_NIGHT_HOURS = set(range(23, 24)) | set(range(0, 5))
PICKUP_GAP_SECONDS = 5 * 60


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def today_key() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _minutes(seconds: int) -> int:
    return int(round(seconds / 60))


def compute(date_key: str) -> Metrics:
    rows = [dict(r) for r in store.sessions_for(date_key)]
    m = Metrics(date_key=date_key)
    if not rows:
        return _with_baseline(m, date_key)

    per_app: dict[str, dict] = defaultdict(lambda: {"seconds": 0, "opens": 0})
    per_cat: dict[str, int] = defaultdict(int)
    hourly = [0] * 24
    total = 0
    prev_end: datetime | None = None
    pickups = 0
    longest_offline = 0

    for r in rows:
        start, end = _parse(r["start_ts"]), _parse(r["end_ts"])
        secs = max(0, int(r["seconds"]))
        total += secs
        label = r["domain"] or r["app"]
        per_app[label]["seconds"] += secs
        per_app[label]["opens"] += 1
        per_app[label]["category"] = r["category"]
        per_cat[r["category"]] += secs

        # Spread the session across the hour buckets it actually touches.
        cursor = start
        while cursor < end:
            bucket_end = min(end, (cursor + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0))
            if bucket_end <= cursor:
                bucket_end = end
            hourly[cursor.hour] += int((bucket_end - cursor).total_seconds())
            if cursor.hour in LATE_NIGHT_HOURS:
                m.late_night_minutes += int((bucket_end - cursor).total_seconds())
            cursor = bucket_end

        if prev_end is not None:
            gap = int((start - prev_end).total_seconds())
            if gap >= PICKUP_GAP_SECONDS:
                pickups += 1
                longest_offline = max(longest_offline, gap)
        else:
            pickups = 1
        prev_end = max(prev_end or end, end)

    longest = max(rows, key=lambda r: r["seconds"])
    m.total_minutes = _minutes(total)
    m.late_night_minutes = _minutes(m.late_night_minutes)
    m.pickups = pickups
    m.switches = len(rows)
    m.longest_session_minutes = _minutes(longest["seconds"])
    m.longest_session_app = longest["domain"] or longest["app"]
    m.first_use_local = _parse(rows[0]["start_ts"]).strftime("%H:%M")
    m.last_use_local = _parse(rows[-1]["end_ts"]).strftime("%H:%M")
    m.longest_offline_block_minutes = _minutes(longest_offline)
    m.by_category = {k: _minutes(v) for k, v in sorted(per_cat.items(), key=lambda kv: -kv[1]) if _minutes(v) > 0}
    m.hourly_minutes = [_minutes(s) for s in hourly]
    m.top_apps = [
        {"name": name, "minutes": _minutes(d["seconds"]), "opens": d["opens"],
         "category": d.get("category", "other")}
        for name, d in sorted(per_app.items(), key=lambda kv: -kv[1]["seconds"])[:6]
        if _minutes(d["seconds"]) >= 1
    ]
    span = (_parse(rows[-1]["end_ts"]) - _parse(rows[0]["start_ts"])).total_seconds()
    m.coverage_hours = round(span / 3600, 1)
    return _with_baseline(m, date_key)


def _with_baseline(m: Metrics, date_key: str) -> Metrics:
    """7-day trailing baseline, so the coach can say 'quieter than usual' honestly."""
    end = datetime.strptime(date_key, "%Y-%m-%d") - timedelta(days=1)
    start = end - timedelta(days=6)
    rows = store.sessions_between(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
    if not rows:
        return m
    per_day: dict[str, int] = defaultdict(int)
    for r in rows:
        per_day[r["date_key"]] += int(r["seconds"])
    m.days_of_history = len(per_day)
    m.baseline_total_minutes = _minutes(int(sum(per_day.values()) / len(per_day)))
    if m.baseline_total_minutes:
        m.delta_vs_baseline_pct = int(
            round((m.total_minutes - m.baseline_total_minutes) / m.baseline_total_minutes * 100))
    return m


def discretionary_minutes(m: Metrics) -> int:
    return sum(v for k, v in m.by_category.items() if k in DISCRETIONARY)


def week_summary(end_key: str) -> dict:
    """Compact 7-day rollup used by the weekly-plan prompt."""
    end = datetime.strptime(end_key, "%Y-%m-%d")
    days = [(end - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]
    out = {"days": [], "totals": defaultdict(int), "worst_hour": 0, "weekday_avg": 0, "weekend_avg": 0}
    hourly_acc = [0] * 24
    wd, we = [], []
    for key in days:
        m = compute(key)
        out["days"].append({
            "date": key,
            "weekday": datetime.strptime(key, "%Y-%m-%d").strftime("%a"),
            "total_minutes": m.total_minutes,
            "discretionary_minutes": discretionary_minutes(m),
            "late_night_minutes": m.late_night_minutes,
            "pickups": m.pickups,
        })
        for cat, mins in m.by_category.items():
            out["totals"][cat] += mins
        for h, v in enumerate(m.hourly_minutes):
            hourly_acc[h] += v
        (we if datetime.strptime(key, "%Y-%m-%d").weekday() >= 5 else wd).append(m.total_minutes)
    out["totals"] = dict(out["totals"])
    out["worst_hour"] = int(max(range(24), key=lambda h: hourly_acc[h]))
    out["weekday_avg"] = int(sum(wd) / len(wd)) if wd else 0
    out["weekend_avg"] = int(sum(we) / len(we)) if we else 0
    out["observed_days"] = sum(1 for d in out["days"] if d["total_minutes"] > 0)
    return out
