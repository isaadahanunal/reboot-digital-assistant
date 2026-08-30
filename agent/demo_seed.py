#!/usr/bin/env python3
"""Seed a realistic 8-day history so the prototype can be demoed without asking a
judge to hand over a week of their own phone data.

The generator is seeded, so the demo is identical every run, and every session it
produces goes through the same /api/ingest path as the real device agent -- there
is no separate "demo mode" code path inside the app.

Persona: a university student in exam season. Studies in blocks on a laptop,
breaks into Instagram, and has a hard late-night stretch between 23:00 and 00:40.
"""
from __future__ import annotations

import argparse
import json
import random
import urllib.request
from datetime import datetime, timedelta

SEED = 20260830

# (app, domain, weight, typical minutes, allowed hour range)
MORNING = [("Instagram", None, 3, (4, 14), (7, 10)),
           ("WhatsApp", None, 3, (2, 8), (7, 10)),
           ("Spotify", None, 2, (3, 10), (7, 10)),
           ("Mail", None, 1, (2, 6), (8, 10))]
STUDY = [("Visual Studio Code", None, 4, (18, 55), (10, 18)),
         ("Google Chrome", "docs.google.com", 3, (10, 35), (10, 18)),
         ("Google Chrome", "stackoverflow.com", 2, (5, 18), (10, 18)),
         ("Notion", None, 2, (8, 25), (10, 18)),
         ("Zoom", None, 1, (25, 50), (10, 16))]
BREAK = [("Instagram", None, 5, (6, 22), (10, 19)),
         ("YouTube", None, 3, (8, 30), (12, 19)),
         ("WhatsApp", None, 3, (3, 12), (10, 19)),
         ("Twitter", None, 2, (5, 16), (10, 19))]
EVENING = [("YouTube", None, 4, (20, 55), (19, 23)),
           ("Netflix", None, 2, (35, 70), (20, 23)),
           ("WhatsApp", None, 3, (4, 15), (19, 23)),
           ("Instagram", None, 3, (10, 28), (19, 23))]
NIGHT = [("Instagram", None, 5, (12, 45), (23, 24)),
         ("TikTok", None, 3, (10, 35), (23, 24)),
         ("YouTube", None, 2, (12, 30), (23, 24))]


def _pick(rng: random.Random, pool):
    return rng.choices(pool, weights=[p[2] for p in pool], k=1)[0]


def _block(rng, day: datetime, pool, start_hour: float, count: int, out: list) -> float:
    cursor = day.replace(hour=int(start_hour), minute=int((start_hour % 1) * 60),
                         second=0, microsecond=0)
    for _ in range(count):
        app, domain, _w, (lo, hi), _hours = _pick(rng, pool)
        minutes = rng.randint(lo, hi)
        end = cursor + timedelta(minutes=minutes)
        out.append({"app": app, "domain": domain,
                    "start": cursor.isoformat(timespec="seconds"),
                    "end": end.isoformat(timespec="seconds"),
                    "device": "demo-laptop", "source": "demo"})
        cursor = end + timedelta(minutes=rng.randint(2, 18))
    return cursor.hour + cursor.minute / 60


def build_day(rng: random.Random, day: datetime, weekend: bool) -> list[dict]:
    out: list[dict] = []
    _block(rng, day, MORNING, 7.6 + rng.random(), rng.randint(2, 4), out)
    if not weekend:
        _block(rng, day, STUDY, 10.2, rng.randint(4, 6), out)
        _block(rng, day, BREAK, 15.5, rng.randint(2, 4), out)
        _block(rng, day, STUDY, 17.0, rng.randint(1, 3), out)
    else:
        _block(rng, day, BREAK, 11.0, rng.randint(4, 7), out)
    _block(rng, day, EVENING, 20.0, rng.randint(2, 4), out)
    # The late-night stretch: heavier at the weekend and towards exam week.
    night_start = day.replace(hour=23, minute=rng.randint(0, 25), second=0, microsecond=0)
    cursor = night_start
    for _ in range(rng.randint(1, 3) + (1 if weekend else 0)):
        app, domain, _w, (lo, hi), _h = _pick(rng, NIGHT)
        minutes = rng.randint(lo, hi)
        end = cursor + timedelta(minutes=minutes)
        if end.hour >= 2 and end.day != cursor.day:
            break
        out.append({"app": app, "domain": domain,
                    "start": cursor.isoformat(timespec="seconds"),
                    "end": end.isoformat(timespec="seconds"),
                    "device": "demo-laptop", "source": "demo"})
        cursor = end + timedelta(minutes=rng.randint(1, 6))
    return out


def build(days: int = 8) -> list[dict]:
    rng = random.Random(SEED)
    today = datetime.now().replace(second=0, microsecond=0)
    sessions: list[dict] = []
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        is_today = offset == 0
        rows = build_day(rng, day, weekend=day.weekday() >= 5)
        if is_today:
            # Only keep what would plausibly have happened by now.
            rows = [r for r in rows if datetime.fromisoformat(r["end"]) <= today]
        sessions.extend(rows)
    return sessions


def main() -> int:
    ap = argparse.ArgumentParser(description="Seed Reboot with a realistic demo week")
    ap.add_argument("--server", default="http://127.0.0.1:8765")
    ap.add_argument("--days", type=int, default=8)
    ap.add_argument("--print", action="store_true", help="print JSON instead of posting")
    args = ap.parse_args()

    sessions = build(args.days)
    if args.print:
        print(json.dumps(sessions, indent=2))
        return 0

    body = json.dumps({"device": "demo-laptop", "source": "demo",
                       "sessions": sessions}).encode()
    req = urllib.request.Request(f"{args.server.rstrip('/')}/api/ingest", data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=20) as resp:
        print(json.dumps(json.loads(resp.read().decode()), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
