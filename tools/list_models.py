#!/usr/bin/env python3
"""List the Gemini models this key can actually call.

Google retires models on its own schedule, so a hard-coded default eventually
404s. Run this, then set REBOOT_GEMINI_MODEL in .env to one of the names printed.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402

from backend import config  # noqa: E402


def main() -> int:
    key = config.load().get("gemini_api_key")
    if not key:
        print("No Gemini key found. Set GEMINI_API_KEY in reboot/.env first.")
        return 1
    with httpx.Client(timeout=30) as client:
        resp = client.get("https://generativelanguage.googleapis.com/v1beta/models",
                          headers={"x-goog-api-key": key}, params={"pageSize": 200})
    if resp.status_code != 200:
        print(f"HTTP {resp.status_code}: {resp.text[:300]}")
        return 1

    usable = [m for m in resp.json().get("models", [])
              if "generateContent" in m.get("supportedGenerationMethods", [])]
    print(f"Currently configured: {config.GEMINI_MODEL}\n")
    print("Text models this key can call:")
    for m in sorted(usable, key=lambda m: m["name"]):
        name = m["name"].removeprefix("models/")
        if any(k in name for k in ("flash", "pro")) and not any(
                k in name for k in ("vision", "tts", "image", "banana", "lyria")):
            mark = "  <- in use" if name == config.GEMINI_MODEL else ""
            print(f"  {name:40} out={m.get('outputTokenLimit')}{mark}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
