"""Local-first SQLite storage.

Nothing here ever leaves the machine on its own: the only outbound call in the
whole project is the one the user explicitly triggers from the Coach screen, and
that call carries the minimised payload built in ``privacy.py``.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Iterator

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  app TEXT NOT NULL,
  domain TEXT,
  category TEXT NOT NULL,
  start_ts TEXT NOT NULL,
  end_ts TEXT NOT NULL,
  seconds INTEGER NOT NULL,
  device TEXT NOT NULL,
  source TEXT NOT NULL,
  date_key TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(app, start_ts, end_ts, device)
);
CREATE INDEX IF NOT EXISTS idx_sessions_date ON sessions(date_key);

CREATE TABLE IF NOT EXISTS kv (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS artifacts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kind TEXT NOT NULL,          -- daily_digest | weekly_plan
  date_key TEXT NOT NULL,
  provider TEXT NOT NULL,
  model TEXT NOT NULL,
  payload TEXT NOT NULL,
  sent_payload TEXT NOT NULL,  -- exactly what left the device (audit trail)
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_artifacts ON artifacts(kind, date_key);

CREATE TABLE IF NOT EXISTS chat (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  role TEXT NOT NULL,          -- user | assistant
  content TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS checkins (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date_key TEXT NOT NULL,
  action_id TEXT NOT NULL,
  status TEXT NOT NULL,
  note TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  UNIQUE(date_key, action_id)
);
"""


@contextmanager
def conn() -> Iterator[sqlite3.Connection]:
    cx = sqlite3.connect(config.DB_PATH)
    cx.row_factory = sqlite3.Row
    try:
        yield cx
        cx.commit()
    finally:
        cx.close()


def init() -> None:
    with conn() as cx:
        cx.executescript(SCHEMA)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def add_sessions(rows: list[dict[str, Any]]) -> int:
    inserted = 0
    with conn() as cx:
        for r in rows:
            try:
                cx.execute(
                    """INSERT OR IGNORE INTO sessions
                       (app, domain, category, start_ts, end_ts, seconds, device, source, date_key, created_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (r["app"], r.get("domain"), r["category"], r["start_ts"], r["end_ts"],
                     r["seconds"], r["device"], r["source"], r["date_key"], _now()),
                )
                inserted += cx.total_changes and 1 or 0
            except sqlite3.DatabaseError:
                continue
    return inserted


def sessions_for(date_key: str) -> list[sqlite3.Row]:
    with conn() as cx:
        return list(cx.execute(
            "SELECT * FROM sessions WHERE date_key=? ORDER BY start_ts", (date_key,)))


def sessions_between(start_key: str, end_key: str) -> list[sqlite3.Row]:
    with conn() as cx:
        return list(cx.execute(
            "SELECT * FROM sessions WHERE date_key BETWEEN ? AND ? ORDER BY start_ts",
            (start_key, end_key)))


def available_dates() -> list[str]:
    with conn() as cx:
        return [r[0] for r in cx.execute(
            "SELECT DISTINCT date_key FROM sessions ORDER BY date_key DESC")]


def devices() -> list[dict[str, Any]]:
    with conn() as cx:
        rows = cx.execute(
            """SELECT device, source, COUNT(*) sessions, MAX(end_ts) last_seen,
                      MIN(date_key) first_day, MAX(date_key) last_day,
                      SUM(seconds) total_seconds
               FROM sessions GROUP BY device, source ORDER BY last_seen DESC""")
        return [dict(r) for r in rows]


def counts() -> dict[str, Any]:
    with conn() as cx:
        total = cx.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        last = cx.execute("SELECT MAX(created_at) FROM sessions").fetchone()[0]
        days = cx.execute("SELECT COUNT(DISTINCT date_key) FROM sessions").fetchone()[0]
    return {"sessions": total, "days": days, "last_ingest": last}


def kv_get(key: str, default: Any = None) -> Any:
    with conn() as cx:
        row = cx.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
    return json.loads(row[0]) if row else default


def kv_set(key: str, value: Any) -> None:
    with conn() as cx:
        cx.execute("INSERT INTO kv(key,value) VALUES(?,?) "
                   "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                   (key, json.dumps(value, ensure_ascii=False)))


def save_artifact(kind: str, date_key: str, provider: str, model: str,
                  payload: dict, sent_payload: dict) -> int:
    with conn() as cx:
        cur = cx.execute(
            """INSERT INTO artifacts(kind,date_key,provider,model,payload,sent_payload,created_at)
               VALUES(?,?,?,?,?,?,?)""",
            (kind, date_key, provider, model,
             json.dumps(payload, ensure_ascii=False),
             json.dumps(sent_payload, ensure_ascii=False), _now()))
        return int(cur.lastrowid or 0)


def latest_artifact(kind: str, date_key: str | None = None) -> dict | None:
    with conn() as cx:
        if date_key:
            row = cx.execute(
                "SELECT * FROM artifacts WHERE kind=? AND date_key=? ORDER BY id DESC LIMIT 1",
                (kind, date_key)).fetchone()
        else:
            row = cx.execute(
                "SELECT * FROM artifacts WHERE kind=? ORDER BY id DESC LIMIT 1", (kind,)).fetchone()
    if not row:
        return None
    return {
        "id": row["id"], "kind": row["kind"], "date_key": row["date_key"],
        "provider": row["provider"], "model": row["model"],
        "created_at": row["created_at"],
        "payload": json.loads(row["payload"]),
        "sent_payload": json.loads(row["sent_payload"]),
    }


def add_checkin(date_key: str, action_id: str, status: str, note: str = "") -> None:
    with conn() as cx:
        cx.execute(
            """INSERT INTO checkins(date_key,action_id,status,note,created_at) VALUES(?,?,?,?,?)
               ON CONFLICT(date_key,action_id) DO UPDATE SET status=excluded.status,
               note=excluded.note, created_at=excluded.created_at""",
            (date_key, action_id, status, note, _now()))


def recent_checkins(days: int = 14) -> list[dict[str, Any]]:
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    with conn() as cx:
        rows = cx.execute(
            "SELECT date_key, action_id, status, note FROM checkins "
            "WHERE date_key >= ? ORDER BY date_key DESC", (since,))
        return [dict(r) for r in rows]


def chat_history(limit: int = 40) -> list[dict[str, Any]]:
    with conn() as cx:
        rows = list(cx.execute(
            "SELECT role, content, created_at FROM chat ORDER BY id DESC LIMIT ?", (limit,)))
    return [dict(r) for r in reversed(rows)]


def add_chat(role: str, content: str) -> None:
    with conn() as cx:
        cx.execute("INSERT INTO chat(role, content, created_at) VALUES(?,?,?)",
                   (role, content, _now()))


def clear_chat() -> None:
    with conn() as cx:
        cx.execute("DELETE FROM chat")


def erase_all() -> None:
    with conn() as cx:
        cx.executescript(
            "DELETE FROM sessions; DELETE FROM artifacts; DELETE FROM checkins; "
            "DELETE FROM chat; DELETE FROM kv;")
