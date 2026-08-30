"""Single normalisation path for incoming sessions.

Both the in-process collector and the HTTP /api/ingest endpoint go through this,
so a session recorded on this machine and a session pushed from a phone export
are validated, categorised and stored by exactly the same code.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

from . import store
from .taxonomy import categorize

MAX_SESSION_SECONDS = 6 * 3600      # clock jumps and sleep/wake artefacts


def normalize(sessions: Iterable[dict[str, Any]], device: str, source: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for s in sessions:
        try:
            start = datetime.fromisoformat(str(s["start"]))
            end = datetime.fromisoformat(str(s["end"]))
        except (KeyError, ValueError):
            continue
        seconds = int((end - start).total_seconds())
        if seconds <= 0 or seconds > MAX_SESSION_SECONDS:
            continue
        app = str(s.get("app") or "").strip()[:120]
        if not app:
            continue
        domain = (str(s.get("domain") or "").strip() or None)
        rows.append({
            "app": app,
            "domain": domain[:120] if domain else None,
            "category": categorize(app, domain),
            "start_ts": start.isoformat(timespec="seconds"),
            "end_ts": end.isoformat(timespec="seconds"),
            "seconds": seconds,
            "device": (s.get("device") or device)[:40],
            "source": s.get("source") or source,
            "date_key": start.strftime("%Y-%m-%d"),
        })
    return rows


def store_sessions(sessions: Iterable[dict[str, Any]], device: str, source: str) -> int:
    rows = normalize(sessions, device, source)
    if rows:
        store.add_sessions(rows)
    return len(rows)
