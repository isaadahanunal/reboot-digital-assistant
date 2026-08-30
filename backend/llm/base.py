"""Provider contract.

Every provider takes (system prompt, user prompt, JSON schema) and returns a
dict matching that schema. Keeping the interface schema-first means the coaching
logic in ``coach.py`` never branches on which model answered.
"""
from __future__ import annotations

from typing import Any, Protocol


class ProviderError(RuntimeError):
    """Raised for anything the caller can present to a user: bad key, quota, refusal."""

    def __init__(self, message: str, *, kind: str = "error", retryable: bool = False):
        super().__init__(message)
        self.kind = kind
        self.retryable = retryable


class CoachProvider(Protocol):
    name: str
    model: str

    def generate_json(self, system: str, user: str, schema: dict[str, Any],
                      context: dict[str, Any] | None = None) -> dict[str, Any]:
        ...

    def generate_text(self, system: str, messages: list[dict[str, str]]) -> str:
        """Free-form reply for the chat surface. `messages` is [{role, content}, ...]."""
        ...


def strip_unsupported(schema: dict[str, Any], allowed: set[str]) -> dict[str, Any]:
    """Recursively keep only schema keywords a given provider understands."""
    out: dict[str, Any] = {}
    for key, value in schema.items():
        if key not in allowed:
            continue
        if key == "properties" and isinstance(value, dict):
            out[key] = {k: strip_unsupported(v, allowed) for k, v in value.items()}
        elif key == "items" and isinstance(value, dict):
            out[key] = strip_unsupported(value, allowed)
        else:
            out[key] = value
    return out
