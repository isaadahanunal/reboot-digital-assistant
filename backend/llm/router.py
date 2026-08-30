"""Provider selection and status reporting."""
from __future__ import annotations

from typing import Any

from .. import config
from .base import ProviderError
from .offline_provider import OfflineProvider


def get_provider(preferred: str | None = None):
    cfg = config.load()
    choice = preferred or cfg.get("provider", "gemini")
    gemini_key, anthropic_key = cfg.get("gemini_api_key", ""), cfg.get("anthropic_api_key", "")

    if choice == "offline":
        return OfflineProvider()
    if choice == "gemini" or (choice == "auto" and gemini_key):
        if not gemini_key:
            raise ProviderError(
                "No Gemini API key yet. Add one in Settings, or switch to Offline mode "
                "to see the rule-based coach.", kind="no_key")
        from .gemini_provider import GeminiProvider
        return GeminiProvider(gemini_key)
    if choice == "anthropic" or (choice == "auto" and anthropic_key):
        if not anthropic_key:
            raise ProviderError("No Anthropic API key configured.", kind="no_key")
        from .anthropic_provider import AnthropicProvider
        return AnthropicProvider(anthropic_key)
    return OfflineProvider()


def provider_status() -> dict[str, Any]:
    cfg = config.load()
    return {
        "selected": cfg.get("provider", "gemini"),
        "gemini_key_set": bool(cfg.get("gemini_api_key")),
        "anthropic_key_set": bool(cfg.get("anthropic_api_key")),
        "gemini_model": config.GEMINI_MODEL,
        "anthropic_model": config.ANTHROPIC_MODEL,
        "key_source": config.key_source(cfg),
        "env_file": str(config.ENV_PATH) if config.ENV_PATH.exists() else None,
    }
