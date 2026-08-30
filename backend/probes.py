"""Platform probes: what is in front, and has the machine been left alone.

This is the only part of Reboot that touches the operating system. It is kept
small and dependency-free on purpose — anyone deciding whether to trust it with
their day should be able to read the whole thing in one sitting.

What it can see
    the frontmost application's name, and (only when domain capture is switched
    on) the host of the active browser tab.

What it cannot see
    keystrokes, window titles, page or message contents, URLs beyond the host,
    file names, screenshots, contacts, location.
"""
from __future__ import annotations

import platform
import re
import subprocess
from datetime import datetime
from urllib.parse import urlparse


def _run(cmd: list[str], timeout: float = 3.0) -> str:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return out.stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return ""


IDLE_CUTOFF_SECONDS = 120          # beyond this the machine counts as unattended
MIN_SESSION_SECONDS = 5            # ignore accidental alt-tabs
BROWSERS = re.compile(r"chrome|safari|firefox|edge|arc|brave|opera", re.I)


class MacProbe:
    system = "macOS"

    def frontmost(self) -> str:
        return _run(["osascript", "-e",
                     'tell application "System Events" to get name of '
                     'first process whose frontmost is true'])

    def idle_seconds(self) -> float:
        raw = _run(["ioreg", "-c", "IOHIDSystem"])
        match = re.search(r'"HIDIdleTime"\s*=\s*(\d+)', raw)
        return int(match.group(1)) / 1e9 if match else 0.0

    def browser_host(self, app: str) -> str | None:
        script = {
            "Google Chrome": 'tell application "Google Chrome" to get URL of active tab of front window',
            "Safari": 'tell application "Safari" to get URL of current tab of front window',
            "Brave Browser": 'tell application "Brave Browser" to get URL of active tab of front window',
            "Microsoft Edge": 'tell application "Microsoft Edge" to get URL of active tab of front window',
        }.get(app)
        if not script:
            return None
        return _host(_run(["osascript", "-e", script]))


class WindowsProbe:
    system = "Windows"

    def frontmost(self) -> str:
        try:
            import ctypes
            from ctypes import wintypes
            user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
            hwnd = user32.GetForegroundWindow()
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            handle = kernel32.OpenProcess(0x1000, False, pid)
            buf = ctypes.create_unicode_buffer(512)
            size = ctypes.c_uint(512)
            kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size))
            kernel32.CloseHandle(handle)
            return buf.value.rsplit("\\", 1)[-1].removesuffix(".exe")
        except Exception:
            return ""

    def idle_seconds(self) -> float:
        try:
            import ctypes

            class LASTINPUTINFO(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

            info = LASTINPUTINFO()
            info.cbSize = ctypes.sizeof(info)
            ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info))
            return (ctypes.windll.kernel32.GetTickCount() - info.dwTime) / 1000.0
        except Exception:
            return 0.0

    def browser_host(self, app: str) -> str | None:
        return None  # no supported API without extra dependencies


class LinuxProbe:
    system = "Linux"

    def frontmost(self) -> str:
        name = _run(["xdotool", "getactivewindow", "getwindowclassname"])
        return name or _run(["xdotool", "getactivewindow", "getwindowname"])[:60]

    def idle_seconds(self) -> float:
        raw = _run(["xprintidle"])
        return float(raw) / 1000.0 if raw.isdigit() else 0.0

    def browser_host(self, app: str) -> str | None:
        return None


def probe_for_platform():
    return {"Darwin": MacProbe, "Windows": WindowsProbe}.get(platform.system(), LinuxProbe)()


def _host(url: str) -> str | None:
    if not url:
        return None
    try:
        host = urlparse(url).hostname or ""
    except ValueError:
        return None
    return host.removeprefix("www.") or None


# ----------------------------------------------------------------- session log
class SessionBuilder:
    """Collapses samples into sessions; only closed sessions are ever sent."""

    def __init__(self) -> None:
        self.current: dict | None = None
        self.closed: list[dict] = []

    def observe(self, app: str, host: str | None, now: datetime) -> None:
        key = (app, host)
        if self.current and (self.current["app"], self.current["domain"]) == key:
            self.current["end"] = now
            return
        self.close(now)
        if app:
            self.current = {"app": app, "domain": host, "start": now, "end": now}

    def close(self, now: datetime) -> None:
        if not self.current:
            return
        span = (self.current["end"] - self.current["start"]).total_seconds()
        if span >= MIN_SESSION_SECONDS:
            self.closed.append({
                "app": self.current["app"],
                "domain": self.current["domain"],
                "start": self.current["start"].isoformat(timespec="seconds"),
                "end": self.current["end"].isoformat(timespec="seconds"),
            })
        self.current = None

    def drain(self) -> list[dict]:
        out, self.closed = self.closed, []
        return out
