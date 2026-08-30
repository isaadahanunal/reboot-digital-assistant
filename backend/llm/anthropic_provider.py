"""Anthropic Claude provider (optional secondary).

Kept because the coaching pipeline is provider-neutral by design and a judge may
want to see the same prompts run against a different model family. Uses the
official SDK and schema-constrained output (`output_config.format`), which is the
Claude equivalent of Gemini's `responseSchema`.
"""
from __future__ import annotations

import json
from typing import Any

from .. import config
from .base import ProviderError


def _strict(schema: dict[str, Any]) -> dict[str, Any]:
    """Claude's strict JSON schema mode requires additionalProperties: false."""
    out = dict(schema)
    if out.get("type") == "object":
        out["additionalProperties"] = False
        out["properties"] = {k: _strict(v) for k, v in out.get("properties", {}).items()}
    if out.get("type") == "array" and isinstance(out.get("items"), dict):
        out["items"] = _strict(out["items"])
    return out


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str, model: str | None = None):
        if not api_key:
            raise ProviderError("No Anthropic API key configured.", kind="no_key")
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover
            raise ProviderError("The 'anthropic' package is not installed.", kind="setup") from exc
        self._anthropic = anthropic
        self._client = anthropic.Anthropic(api_key=api_key, timeout=120.0)
        self.model = model or config.ANTHROPIC_MODEL

    def generate_json(self, system: str, user: str, schema: dict[str, Any],
                      context: dict[str, Any] | None = None) -> dict[str, Any]:
        anthropic = self._anthropic
        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=8000,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_config={"format": {"type": "json_schema", "schema": _strict(schema)},
                               "effort": "medium"},
            )
        except anthropic.AuthenticationError as exc:
            raise ProviderError("Anthropic rejected the API key.", kind="auth") from exc
        except anthropic.RateLimitError as exc:
            raise ProviderError("Anthropic rate limit reached.", kind="rate_limit",
                                retryable=True) from exc
        except anthropic.APIConnectionError as exc:
            raise ProviderError(f"Could not reach Anthropic: {exc}", kind="network",
                                retryable=True) from exc
        except anthropic.APIStatusError as exc:
            raise ProviderError(f"Anthropic error {exc.status_code}.", kind="api",
                                retryable=exc.status_code >= 500) from exc

        if getattr(response, "stop_reason", None) == "refusal":
            raise ProviderError("Claude declined to answer this request.", kind="blocked")
        text = next((b.text for b in response.content if b.type == "text"), "")
        if not text:
            raise ProviderError("Claude returned no text block.", kind="empty", retryable=True)
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ProviderError("Claude returned malformed JSON.", kind="parse") from exc

    def generate_text(self, system: str, messages: list[dict[str, str]]) -> str:
        anthropic = self._anthropic
        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=system,
                messages=[{"role": m["role"], "content": m["content"]} for m in messages],
                output_config={"effort": "low"},
            )
        except anthropic.APIStatusError as exc:
            raise ProviderError(f"Anthropic error {exc.status_code}.", kind="api",
                                retryable=exc.status_code >= 500) from exc
        if getattr(response, "stop_reason", None) == "refusal":
            raise ProviderError("Claude declined to answer this message.", kind="blocked")
        return next((b.text for b in response.content if b.type == "text"), "").strip()
