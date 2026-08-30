"""Google Gemini provider -- the primary coach model for this build.

Notes that matter for the write-up:

* The key travels in the ``x-goog-api-key`` header, not in the query string as
  the first prototype did. Query strings end up in proxy logs, shell history and
  browser history; a header does not.
* ``responseSchema`` + ``responseMimeType: application/json`` gives us
  schema-constrained decoding, so the JSON-parsing failure path in the original
  single-file prototype simply cannot happen.
* ``temperature`` is low (0.4). This is advice, not creative writing; run-to-run
  volatility in a well-being plan reads as the tool being unreliable.
"""
from __future__ import annotations

import json
import time
from typing import Any

try:  # anthropic 1.x pulls in httpx2; either client works here.
    import httpx
except ImportError:  # pragma: no cover
    import httpx2 as httpx  # type: ignore

from .. import config
from .base import ProviderError, strip_unsupported

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# Gemini's Schema object is an OpenAPI subset with UPPERCASE type names.
_GEMINI_KEYS = {"type", "properties", "required", "items", "enum", "description",
                "minItems", "maxItems", "nullable", "format"}
_TYPE_MAP = {"object": "OBJECT", "array": "ARRAY", "string": "STRING",
             "integer": "INTEGER", "number": "NUMBER", "boolean": "BOOLEAN"}


def to_gemini_schema(schema: dict[str, Any]) -> dict[str, Any]:
    out = strip_unsupported(schema, _GEMINI_KEYS)
    if "type" in out:
        out["type"] = _TYPE_MAP.get(out["type"], out["type"])
    if "properties" in out:
        out["properties"] = {k: to_gemini_schema(v) for k, v in schema.get("properties", {}).items()}
        # Stable field order makes streamed/partial output readable and diffs stable.
        out["propertyOrdering"] = list(out["properties"].keys())
    if "items" in out and isinstance(schema.get("items"), dict):
        out["items"] = to_gemini_schema(schema["items"])
    if out.get("enum") and out.get("type") == "STRING":
        out["format"] = "enum"   # Gemini requires this marker for enum-constrained strings
    return out


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str | None = None):
        if not api_key:
            raise ProviderError("No Gemini API key configured.", kind="no_key")
        self._key = api_key
        self.model = model or config.GEMINI_MODEL

    def _generation_config(self, schema: dict[str, Any]) -> dict[str, Any]:
        cfg: dict[str, Any] = {
            "responseMimeType": "application/json",
            "responseSchema": to_gemini_schema(schema),
            "temperature": 0.4,
            "topP": 0.9,
            # Thinking tokens count against this ceiling, so it is set far above the
            # ~900 tokens the JSON itself needs.
            "maxOutputTokens": 16384,
        }
        # thinkingLevel is a Gemini 3 field; sending it to a 2.x model is a 400.
        if self.model.startswith("gemini-3"):
            cfg["thinkingConfig"] = {"thinkingLevel": config.GEMINI_THINKING}
        return cfg

    def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        """One HTTP path for both surfaces, including the retry and error mapping.

        A flash model returning 503 "high demand" is common enough that failing a
        whole digest on the first attempt is the wrong default during a demo.
        """
        url = ENDPOINT.format(model=self.model)
        for attempt in range(2):
            try:
                with httpx.Client(timeout=120.0) as client:
                    resp = client.post(
                        url,
                        headers={"x-goog-api-key": self._key, "Content-Type": "application/json"},
                        json=body,
                    )
            except Exception as exc:
                if attempt == 0:
                    time.sleep(2.0)
                    continue
                raise ProviderError(f"Could not reach Gemini: {exc}", kind="network",
                                    retryable=True) from exc
            if resp.status_code in (429, 503) and attempt == 0:
                time.sleep(2.0)
                continue
            break

        if resp.status_code in (401, 403):
            raise ProviderError("Gemini rejected the API key (401/403). Check your .env file.",
                                kind="auth")
        if resp.status_code == 429:
            raise ProviderError("Gemini rate limit reached. Wait a minute and retry.",
                                kind="rate_limit", retryable=True)
        if resp.status_code == 404:
            raise ProviderError(
                f"Gemini has no model '{self.model}' available to this key ({_short(resp.text)}) "
                "Set REBOOT_GEMINI_MODEL in .env to a model your key can use, then restart. "
                "`python3 tools/list_models.py` lists them.", kind="model")
        if resp.status_code >= 400:
            raise ProviderError(f"Gemini error {resp.status_code}: {_short(resp.text)}", kind="api",
                                retryable=resp.status_code >= 500)

        data = resp.json()
        if not data.get("candidates"):
            reason = (data.get("promptFeedback") or {}).get("blockReason", "unknown")
            raise ProviderError(f"Gemini returned no candidate (reason: {reason}).", kind="blocked")
        return data

    def generate_json(self, system: str, user: str, schema: dict[str, Any],
                      context: dict[str, Any] | None = None) -> dict[str, Any]:
        data = self._post({
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": self._generation_config(schema),
        })
        cand = data["candidates"][0]
        finish = cand.get("finishReason")
        if finish in ("SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST"):
            raise ProviderError("Gemini's safety filter blocked this response.", kind="blocked")
        parts = (cand.get("content") or {}).get("parts") or []
        text = "".join(part.get("text", "") for part in parts).strip()
        if finish == "MAX_TOKENS" and not text:
            raise ProviderError(
                "Gemini hit the output token ceiling before writing the JSON. Try again.",
                kind="truncated", retryable=True)
        if not text:
            raise ProviderError(f"Gemini returned an empty response (finishReason={finish}).",
                                kind="empty", retryable=True)
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ProviderError("Gemini returned malformed JSON despite the response schema.",
                                kind="parse") from exc

    def generate_text(self, system: str, messages: list[dict[str, str]]) -> str:
        """Conversational turn. No responseSchema -- the chat answers in prose."""
        contents = [{"role": "model" if m["role"] == "assistant" else "user",
                     "parts": [{"text": m["content"]}]} for m in messages]
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": contents,
            "generationConfig": {
                "temperature": 0.6,          # a shade warmer than the digest; still not creative writing
                "topP": 0.9,
                "maxOutputTokens": 2048,
                **({"thinkingConfig": {"thinkingLevel": config.GEMINI_THINKING}}
                   if self.model.startswith("gemini-3") else {}),
            },
        }
        data = self._post(body)
        cand = (data.get("candidates") or [{}])[0]
        if cand.get("finishReason") in ("SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST"):
            raise ProviderError("Gemini's safety filter blocked this reply.", kind="blocked")
        parts = (cand.get("content") or {}).get("parts") or []
        text = "".join(part.get("text", "") for part in parts).strip()
        if not text:
            raise ProviderError("Gemini returned an empty reply.", kind="empty", retryable=True)
        return text


def _short(text: str, limit: int = 240) -> str:
    try:
        payload = json.loads(text)
        msg = payload.get("error", {}).get("message", text)
    except Exception:
        msg = text
    return msg[:limit]
