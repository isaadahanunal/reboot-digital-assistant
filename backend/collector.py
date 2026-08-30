"""In-process usage collector.

Why this lives in the server rather than only in a separate script: a tool the
user has to keep a terminal open for is a tool they will stop using by Thursday.
The server is already running whenever they use the app, so the sampler runs as
a background thread inside it, controlled from the interface, and it keeps
recording after the browser tab is closed.

Reboot measures the machine it runs on and nothing else. Phone imports and
remote agents were removed deliberately: each one added a data path whose
accuracy could not be verified from here, and a promise the prototype could not
keep.

What it records is unchanged: the frontmost application's name and how long it
was in front, plus the browser host only when domain capture is explicitly on.
Idle time beyond two minutes is excluded rather than billed as screen time.
"""
from __future__ import annotations

import os
import platform
import threading
from datetime import datetime, timedelta
from typing import Any

from . import config, ingest
from .probes import BROWSERS, IDLE_CUTOFF_SECONDS, SessionBuilder, probe_for_platform

LOCK_PATH = None          # set on first start; lives next to the database
SAMPLE_SECONDS = 4.0
FLUSH_SECONDS = 20.0
# If the probe returns nothing this many times in a row, the platform is almost
# certainly withholding permission rather than reporting an idle desktop.
BLIND_SAMPLES_BEFORE_HINT = 5

PERMISSION_HINT = {
    "Darwin": ("macOS needs Automation permission before it will name the frontmost app. "
               "Look for the permission prompt, or enable it under System Settings → "
               "Privacy & Security → Automation for the terminal running Reboot."),
    "Linux": ("On Linux the collector needs xdotool and xprintidle installed, and an X11 "
              "session (Wayland does not expose the active window)."),
    "Windows": "Windows should not need extra permission; if this persists, check your security software.",
}


def _process_alive(pid: int) -> bool:
    """Signal 0 asks 'does this pid exist and may I signal it'.

    PermissionError means it exists but belongs to someone else -- that counts as
    alive. Treating it as dead (the obvious `except OSError: return False`) makes
    the lock useless against exactly the processes it should protect against.
    """
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


class SingleInstance:
    """A PID file that stops two servers from recording the same day twice.

    Found the hard way: two Reboot servers left running against one database
    produced overlapping sessions for the same real activity, which silently
    doubles every number the coach reasons about. Measurement has to be
    single-writer, and the guard belongs in code rather than in a README warning.
    """

    def __init__(self, path):
        self.path = path

    def acquire(self) -> tuple[bool, str]:
        if self.path.exists():
            try:
                pid = int(self.path.read_text("utf-8").strip() or 0)
            except (OSError, ValueError):
                pid = 0
            if pid and pid != os.getpid() and _process_alive(pid):
                return False, (f"Another Reboot process (pid {pid}) is already recording on this "
                               "machine. Stop it first, or two servers will double-count the same "
                               "screen time.")
        try:
            self.path.write_text(str(os.getpid()), encoding="utf-8")
        except OSError as exc:
            return False, f"Could not write the collector lock: {exc}"
        return True, ""

    def release(self) -> None:
        try:
            if self.path.exists() and self.path.read_text("utf-8").strip() == str(os.getpid()):
                self.path.unlink()
        except OSError:
            pass


class Collector:
    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.RLock()
        self._probe = probe_for_platform()
        self._lockfile = SingleInstance(config.DATA_DIR / "collector.lock")
        self._state: dict[str, Any] = {
            "running": False,
            "platform": self._probe.system,
            "device": platform.node()[:40] or "this-computer",
            "capture_domains": False,
            "started_at": None,
            "last_sample_at": None,
            "current_app": None,
            "idle": False,
            "sessions_captured": 0,
            "blind_samples": 0,
            "permission_hint": None,
            "blocked_reason": None,
        }

    # ------------------------------------------------------------- lifecycle
    def start(self, capture_domains: bool | None = None) -> dict[str, Any]:
        with self._lock:
            if self._state["running"]:
                return self.status()
            if capture_domains is not None:
                self._state["capture_domains"] = bool(capture_domains)
            acquired, reason = self._lockfile.acquire()
            if not acquired:
                self._state.update({"running": False, "blocked_reason": reason})
                return self.status()
            self._stop.clear()
            self._state.update({
                "running": True,
                "started_at": datetime.now().isoformat(timespec="seconds"),
                "blind_samples": 0,
                "permission_hint": None,
                "blocked_reason": None,
            })
            self._thread = threading.Thread(target=self._loop, name="reboot-collector", daemon=True)
            self._thread.start()
            return self.status()

    def stop(self) -> dict[str, Any]:
        self._stop.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=SAMPLE_SECONDS + 2)
        self._lockfile.release()
        with self._lock:
            self._state.update({"running": False, "current_app": None, "blocked_reason": None})
        return self.status()

    def status(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._state)

    # ------------------------------------------------------------------ loop
    def _loop(self) -> None:
        builder = SessionBuilder()
        last_flush = datetime.now()
        while not self._stop.is_set():
            now = datetime.now()
            try:
                idle = self._probe.idle_seconds()
                if idle > IDLE_CUTOFF_SECONDS:
                    # Close the open stretch at the moment activity actually stopped.
                    builder.close(now - timedelta(seconds=idle))
                    self._note(current_app=None, idle=True, last_sample_at=now)
                else:
                    app = self._probe.frontmost()
                    host = None
                    if app and self._state["capture_domains"] and BROWSERS.search(app):
                        host = self._probe.browser_host(app)
                    builder.observe(app, host, now)
                    self._note(current_app=app or None, idle=False, last_sample_at=now)
                    self._track_blindness(bool(app))
            except Exception as exc:                     # a probe failure must not kill the thread
                self._note(permission_hint=f"Collector error: {exc}")

            if (now - last_flush).total_seconds() >= FLUSH_SECONDS:
                self._flush(builder)
                last_flush = now
            self._stop.wait(SAMPLE_SECONDS)

        builder.close(datetime.now())
        self._flush(builder)

    def _flush(self, builder: SessionBuilder) -> None:
        # Only completed sessions are stored; the stretch still in progress stays
        # open so one continuous hour is not chopped into flush-sized pieces.
        batch = builder.drain()
        if not batch:
            return
        stored = ingest.store_sessions(batch, self._state["device"], "agent")
        self._note(sessions_captured=self._state["sessions_captured"] + stored)

    def _track_blindness(self, saw_app: bool) -> None:
        if saw_app:
            self._note(blind_samples=0, permission_hint=None)
            return
        blind = self._state["blind_samples"] + 1
        hint = PERMISSION_HINT.get(self._probe.system) if blind >= BLIND_SAMPLES_BEFORE_HINT else None
        self._note(blind_samples=blind, permission_hint=hint)

    def _note(self, **fields: Any) -> None:
        with self._lock:
            self._state.update(fields)


collector = Collector()


def autostart_if_enabled() -> None:
    """Called on server startup so measurement does not depend on remembering."""
    cfg = config.load()
    if cfg.get("collector_autostart"):
        collector.start(cfg.get("capture_domains", False))
