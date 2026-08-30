"""Runtime configuration for Reboot.

Design note (privacy): the API key never lives in the browser. It is never
returned to the frontend either -- the API only reports whether one is set.

Key resolution order, highest wins:
    1. a real environment variable  (export GEMINI_API_KEY=...)
    2. reboot/.env                  (loaded here, no third-party dependency)
    3. data/config.json             (written by the Engine settings dialog, mode 0600)

.env is the convenient path for development and for handing the project to
someone else; the settings dialog is the path for a user who never opens a
terminal. Both end up in the same place.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = Path(os.environ.get("REBOOT_ENV_FILE", ROOT / ".env"))


def _load_dotenv(path: Path = ENV_PATH) -> set[str]:
    """Minimal KEY=VALUE reader. A real environment variable always wins.

    Deliberately dependency-free and deliberately dumb: it handles comments,
    blank lines, `export ` prefixes and surrounding quotes, and nothing else.
    """
    loaded: set[str] = set()
    if not path.exists():
        return loaded
    try:
        lines = path.read_text("utf-8").splitlines()
    except OSError:
        return loaded
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.removeprefix("export ").partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
            loaded.add(key)
    return loaded


DOTENV_KEYS = _load_dotenv()

DATA_DIR = Path(os.environ.get("REBOOT_DATA_DIR", ROOT / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "reboot.db"
CONFIG_PATH = DATA_DIR / "config.json"

# The frontend is a React/Vite bundle. WEB_DIR points at the build output; when
# it is missing the server serves a short "run the build" page instead of 404ing,
# so a fresh clone explains itself rather than looking broken.
WEB_DIR = ROOT / "ui" / "dist"
UI_SRC_DIR = ROOT / "ui"


def ui_built() -> bool:
    return (WEB_DIR / "index.html").exists()

# Gemini is the primary coach model for this build (the key the team connects is
# a Google AI Studio key). Claude is kept as an optional secondary provider, and
# an offline heuristic engine keeps the prototype demonstrable with no key at all.
ANTHROPIC_MODEL = os.environ.get("REBOOT_ANTHROPIC_MODEL", "claude-opus-5")
GEMINI_MODEL = os.environ.get("REBOOT_GEMINI_MODEL", "gemini-3.6-flash")
# Gemini 3 thinks by default. Measured on this project's own prompts: "low" runs in
# ~6s versus ~35s, produces the same schema-valid output, and cited no ungrounded
# numbers -- the digest prompt already carries its reasoning procedure explicitly,
# so the model has little left to work out for itself. Set to "high" for harder cases.
GEMINI_THINKING = os.environ.get("REBOOT_GEMINI_THINKING", "low")

_DEFAULTS = {
    "provider": "gemini",        # gemini | anthropic | offline | auto
    "anthropic_api_key": "",
    "gemini_api_key": "",
    "capture_domains": False,    # opt-in: browser domain capture by the collector
    "collector_autostart": True, # keep measuring whenever the server is up
}


def _read_file_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text("utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def key_source(cfg: dict) -> dict[str, str]:
    """Where each key actually came from -- surfaced in the settings dialog so a
    user is never editing a field that a .env silently overrides."""
    def origin(env_names: tuple[str, ...], stored: str) -> str:
        for name in env_names:
            if os.environ.get(name):
                return ".env" if name in DOTENV_KEYS else "environment"
        return "settings" if stored else "none"

    return {
        "gemini": origin(("GEMINI_API_KEY", "GOOGLE_API_KEY"), _read_file_config().get("gemini_api_key", "")),
        "anthropic": origin(("ANTHROPIC_API_KEY",), _read_file_config().get("anthropic_api_key", "")),
    }


def load() -> dict:
    cfg = dict(_DEFAULTS)
    cfg.update(_read_file_config())
    # Environment (including anything .env put there) wins over the on-disk file.
    if os.environ.get("ANTHROPIC_API_KEY"):
        cfg["anthropic_api_key"] = os.environ["ANTHROPIC_API_KEY"]
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        cfg["gemini_api_key"] = os.environ.get("GEMINI_API_KEY") or os.environ["GOOGLE_API_KEY"]
    if os.environ.get("REBOOT_PROVIDER"):
        cfg["provider"] = os.environ["REBOOT_PROVIDER"]
    return cfg


def save(patch: dict) -> dict:
    cfg = dict(_DEFAULTS)
    cfg.update(_read_file_config())
    for key, value in patch.items():
        if key in _DEFAULTS and value is not None:
            cfg[key] = value
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    os.chmod(CONFIG_PATH, 0o600)
    return load()
