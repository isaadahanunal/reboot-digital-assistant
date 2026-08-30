"""Pydantic schemas shared by the API, the device agent and the LLM layer."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

Category = Literal[
    "social", "entertainment", "communication", "work", "reading",
    "games", "shopping", "utility", "other",
]


class UsageSession(BaseModel):
    """One uninterrupted foreground stretch of a single app, as seen on device."""

    app: str
    start: str                      # ISO-8601 local time
    end: str
    domain: Optional[str] = None    # only when the user opted into domain capture
    device: str = "desktop"
    source: str = "agent"           # agent | import | demo


class IngestPayload(BaseModel):
    device: str = "desktop"
    source: str = "agent"
    sessions: list[UsageSession] = Field(default_factory=list)


class Profile(BaseModel):
    """Everything the user tells us about themselves. Stored locally only."""

    goal: str = "Reduce doomscrolling"
    trigger: str = "Late at night in bed"
    context: str = ""
    daily_target_minutes: int = 180
    tone: Literal["gentle", "direct"] = "gentle"
    language: Literal["en", "tr"] = "en"
    age_band: Literal["under_18", "18_24", "25_39", "40_plus", "undisclosed"] = "undisclosed"
    onboarded: bool = False           # has the first-run setup been completed?
    consent_analytics: bool = False   # may aggregated metrics leave the device?
    consent_context: bool = False     # may the free-text context leave the device?
    share_app_names: bool = True      # send real app names, or category-only?


class CheckIn(BaseModel):
    date_key: str
    action_id: str
    status: Literal["done", "partial", "skipped", "too_hard"]
    note: str = ""


class Metrics(BaseModel):
    """Deterministic, on-device aggregation. This is the *only* thing the model sees."""

    date_key: str
    total_minutes: int = 0
    pickups: int = 0
    switches: int = 0
    longest_session_minutes: int = 0
    longest_session_app: str = ""
    late_night_minutes: int = 0
    first_use_local: str = ""
    last_use_local: str = ""
    longest_offline_block_minutes: int = 0
    by_category: dict[str, int] = Field(default_factory=dict)
    top_apps: list[dict[str, Any]] = Field(default_factory=list)
    hourly_minutes: list[int] = Field(default_factory=lambda: [0] * 24)
    baseline_total_minutes: int = 0
    delta_vs_baseline_pct: int = 0
    days_of_history: int = 0
    coverage_hours: float = 0.0       # how much of the day the agent actually observed


class GenerateRequest(BaseModel):
    date_key: Optional[str] = None
    force: bool = False
