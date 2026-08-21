"""HTTP / service schemas for the voice channel."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class VoiceCallStartRequest(BaseModel):
    """Start a voice call session and CallLog row."""

    call_id: str = Field(min_length=1, max_length=128)
    caller_phone: str | None = Field(default=None, max_length=32)
    caller_name: str | None = Field(default=None, max_length=120)
    provider: str | None = None


class VoiceCallStartResponse(BaseModel):
    success: bool = True
    call_id: str
    customer_id: UUID | None = None
    provider: str
    provider_session: dict[str, Any] = Field(default_factory=dict)
    greeting: str | None = None


class VoiceTurnRequest(BaseModel):
    """One transcribed caller utterance for the booking agent."""

    call_id: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1, max_length=4000)
    caller_phone: str | None = Field(default=None, max_length=32)
    interrupted: bool = False


class VoiceTurnResponse(BaseModel):
    success: bool = True
    call_id: str
    reply: str
    booking_id: UUID | None = None
    outcome_hint: str | None = None


class VoiceCallEndRequest(BaseModel):
    call_id: str = Field(min_length=1, max_length=128)
    duration_seconds: int | None = Field(default=None, ge=0)
    outcome: Literal[
        "booking_created",
        "information_request",
        "cancelled",
        "no_booking",
    ] | None = None


class VoiceCallEndResponse(BaseModel):
    success: bool = True
    call_id: str
    outcome: str
    booking_id: UUID | None = None
    duration_seconds: int | None = None
    ended_at: datetime | None = None


class VoiceToolExecuteRequest(BaseModel):
    """
    Execute a Phase 5 tool for a live call.

    Used when a voice provider (e.g. Uplift client-side RPC handler) proxies
    tool calls to this backend instead of talking to the database itself.
    """

    call_id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=64)
    arguments: dict[str, Any] = Field(default_factory=dict)
    caller_phone: str | None = Field(default=None, max_length=32)


class VoiceToolExecuteResponse(BaseModel):
    success: bool
    call_id: str
    name: str
    result: dict[str, Any]
    # Uplift-friendly optional spoken hint (never includes secrets).
    presentation_instructions: str | None = None


class VoiceWebhookEvent(BaseModel):
    """
    Canonical Sparkle voice event envelope.

    Uplift's documented tool path is client-side RPC (not a documented
    server webhook). This envelope is our secured internal contract for
    adapters that forward lifecycle events into Sparkle.
    """

    event_type: Literal["call.started", "call.ended", "call.turn", "tool.execute"]
    call_id: str = Field(min_length=1, max_length=128)
    timestamp: datetime | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
