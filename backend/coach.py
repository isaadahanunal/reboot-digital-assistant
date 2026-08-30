"""Orchestration: measurement -> minimisation -> generation -> guardrails -> storage.

The order matters and is the whole argument of the project:

    aggregate.compute      deterministic numbers, computed locally
    privacy.build_payload  minimised, redacted, consent-gated
    safety.screen_input    refuse to coach through a crisis signal
    provider.generate_json schema-constrained generation
    safety.screen_output   deterministic rule check on what came back
    prompts.revision       one bounded repair attempt if a rule tripped
    safety.neutralize      last-resort scrub, with the failure surfaced in the UI
    store.save_artifact    keep the exact sent payload for auditability
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from . import aggregate, prompts, privacy, safety, store
from .llm import ProviderError, get_provider
from .models import Profile


def load_profile() -> Profile:
    return Profile(**(store.kv_get("profile") or {}))


def save_profile(profile: Profile) -> Profile:
    store.kv_set("profile", profile.model_dump())
    return profile


def _envelope(kind: str, date_key: str, provider: Any, content: dict,
              sent_payload: dict, flags: list[str], revised: bool,
              injection_suspected: bool) -> dict:
    return {
        "kind": kind,
        "date_key": date_key,
        "provider": provider.name,
        "model": provider.model,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "content": content,
        "meta": {
            "data_confidence": safety.confidence_for(sent_payload),
            "guardrail_flags": flags,
            "revised": revised,
            "ai_generated": provider.name != "offline",
            "injection_suspected": injection_suspected,
            "disclaimer": safety.DISCLAIMER,
        },
        "sent_payload": sent_payload,
    }


def _guarded_generate(provider, system: str, user: str, schema: dict,
                      context: dict) -> tuple[dict, list[str], bool]:
    """Generate, check, and repair once if the deterministic checker complains."""
    content = provider.generate_json(system, user, schema, context)
    content, flags = safety.screen_output(content)
    revised = False
    if flags and provider.name != "offline":
        try:
            repaired = provider.generate_json(
                system, prompts.revision_prompt(flags, content), schema, context)
            repaired, flags_after = safety.screen_output(repaired)
            revised = True
            if not flags_after:
                return repaired, [], True
            content, flags = safety.neutralize(repaired), flags_after
        except ProviderError:
            content = safety.neutralize(content)
    elif flags:
        content = safety.neutralize(content)
    return content, flags, revised


def _effective_provider(preferred: str | None) -> str:
    from . import config
    return preferred or config.load().get("provider", "gemini")


def _consent_gate(profile: Profile, provider_name: str) -> None:
    """Checked before a provider is even constructed: consent gates the call, not the key."""
    if provider_name == "offline":
        return
    if not profile.consent_analytics:
        raise ProviderError(
            "Sending your daily metrics to an AI provider needs your explicit consent.",
            kind="consent")


def generate_daily(date_key: str | None = None, preferred_provider: str | None = None) -> dict:
    date_key = date_key or aggregate.today_key()
    profile = load_profile()
    metrics = aggregate.compute(date_key)
    checkins = store.recent_checkins()
    payload = privacy.build_payload(metrics, profile, checkins)
    payload["_kind"] = "daily_digest"

    gate = safety.screen_input(profile.context)
    if gate["block_generation"]:
        return {"kind": "support_card", "date_key": date_key, "content": gate["card"],
                "meta": {"blocked": True, "reason": "crisis_signal",
                         "disclaimer": safety.DISCLAIMER}}

    _consent_gate(profile, _effective_provider(preferred_provider))
    provider = get_provider(preferred_provider)

    user_prompt = prompts.daily_digest_prompt(
        payload, profile.goal, profile.trigger, profile.tone, profile.language)
    content, flags, revised = _guarded_generate(
        provider, prompts.daily_digest_system(), user_prompt, prompts.DAILY_DIGEST_SCHEMA, payload)

    injection = _looks_like_injection(profile.context)
    envelope = _envelope("daily_digest", date_key, provider, content, payload,
                         flags, revised, injection)
    store.save_artifact("daily_digest", date_key, provider.name, provider.model,
                        envelope, payload)
    return envelope


def generate_weekly(date_key: str | None = None, preferred_provider: str | None = None) -> dict:
    date_key = date_key or aggregate.today_key()
    profile = load_profile()
    metrics = aggregate.compute(date_key)
    checkins = store.recent_checkins()
    week = aggregate.week_summary(date_key)
    payload = privacy.build_payload(metrics, profile, checkins, week=week)
    payload["_kind"] = "weekly_plan"

    gate = safety.screen_input(profile.context)
    if gate["block_generation"]:
        return {"kind": "support_card", "date_key": date_key, "content": gate["card"],
                "meta": {"blocked": True, "reason": "crisis_signal",
                         "disclaimer": safety.DISCLAIMER}}

    _consent_gate(profile, _effective_provider(preferred_provider))
    provider = get_provider(preferred_provider)

    user_prompt = prompts.weekly_plan_prompt(
        payload, profile.tone, profile.language, with_adaptation=bool(checkins))
    content, flags, revised = _guarded_generate(
        provider, prompts.daily_digest_system(), user_prompt, prompts.WEEKLY_PLAN_SCHEMA, payload)

    envelope = _envelope("weekly_plan", date_key, provider, content, payload, flags,
                         revised, _looks_like_injection(profile.context))
    store.save_artifact("weekly_plan", date_key, provider.name, provider.model,
                        envelope, payload)
    return envelope


_INJECTION_HINTS = ("ignore previous", "ignore your", "system prompt", "disregard the",
                    "you are now", "act as", "önceki talimat", "sistem komut")


def _looks_like_injection(text: str) -> bool:
    low = (text or "").lower()
    return any(hint in low for hint in _INJECTION_HINTS)


def preview_payload(date_key: str | None = None, kind: str = "daily_digest") -> dict:
    """Exactly what would leave the device -- shown in the UI before any call."""
    date_key = date_key or aggregate.today_key()
    profile = load_profile()
    metrics = aggregate.compute(date_key)
    week = aggregate.week_summary(date_key) if kind == "weekly_plan" else None
    payload = privacy.build_payload(metrics, profile, store.recent_checkins(), week=week)
    payload["_kind"] = kind
    return payload


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------
MAX_TURNS = 16          # keeps the request bounded; the data block is resent each turn


def chat_context(date_key: str | None = None) -> dict:
    """The same minimised, consent-gated payload the digest gets, plus a short
    summary of what the coach has already told this user, so the conversation can
    refer back to its own plan instead of contradicting it."""
    date_key = date_key or aggregate.today_key()
    profile = load_profile()
    metrics = aggregate.compute(date_key)
    payload = privacy.build_payload(metrics, profile, store.recent_checkins(),
                                    week=aggregate.week_summary(date_key))
    digest = store.latest_artifact("daily_digest")
    plan = store.latest_artifact("weekly_plan")
    if digest:
        content = digest["payload"].get("content", {})
        payload["last_digest"] = {
            "date": digest["date_key"],
            "headline": content.get("headline"),
            "confidence": content.get("confidence"),
            "experiments": [e.get("title") for e in content.get("micro_experiments", [])],
        }
    if plan:
        content = plan["payload"].get("content", {})
        payload["current_plan"] = {
            "title": content.get("plan_title"),
            "target": content.get("weekly_target"),
            "days": [{"day": d.get("day"), "focus": d.get("focus")} for d in content.get("days", [])],
        }
    return payload


def chat(message: str, preferred_provider: str | None = None) -> dict:
    """One conversational turn, through the same gates as every other generation."""
    message = (message or "").strip()
    if not message:
        raise ProviderError("Empty message.", kind="empty_input")

    profile = load_profile()

    # The crisis gate runs on what the user just typed, before any network call.
    gate = safety.screen_input(message, profile.context)
    if gate["block_generation"]:
        # Deliberately not stored. Writing it to history would (a) hand the text to
        # the model on the *next* turn, quietly undoing the gate one message later,
        # and (b) keep a record of someone's worst moment that they never agreed to.
        return {"kind": "support_card", "content": gate["card"],
                "meta": {"blocked": True, "reason": "crisis_signal",
                         "disclaimer": safety.DISCLAIMER}}

    _consent_gate(profile, _effective_provider(preferred_provider))
    provider = get_provider(preferred_provider)

    payload = chat_context()
    payload["_kind"] = "chat"
    system = prompts.chat_system(payload, profile.tone, profile.language)

    history = store.chat_history(MAX_TURNS)
    turns = [{"role": m["role"], "content": m["content"]} for m in history]
    turns.append({"role": "user", "content": message})

    reply = provider.generate_text(system, turns)
    reply, flags = safety.screen_output({"reply": reply})
    if flags:
        reply = safety.neutralize(reply)
    text = reply["reply"].strip()

    store.add_chat("user", message)
    store.add_chat("assistant", text)
    return {
        "kind": "message",
        "content": text,
        "meta": {
            "provider": provider.name,
            "model": provider.model,
            "guardrail_flags": flags,
            "injection_suspected": _looks_like_injection(message),
            "disclaimer": safety.DISCLAIMER,
        },
    }
