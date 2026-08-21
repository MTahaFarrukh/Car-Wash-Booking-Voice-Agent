"""Provider-agnostic voice events and tool calls."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


VoiceEventType = Literal[
    "call.started",
    "call.ended",
    "call.turn",
    "tool.execute",
    "user.interrupted",
    "ignored",
]


@dataclass
class NormalizedVoiceToolCall:
    """Channel-neutral tool invocation produced by any voice provider adapter."""

    id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizedVoiceEvent:
    """Channel-neutral lifecycle / interaction event."""

    event_type: VoiceEventType
    call_id: str
    provider: str
    caller_phone: str | None = None
    caller_name: str | None = None
    text: str | None = None
    interrupted: bool = False
    duration_seconds: int | None = None
    outcome: str | None = None
    tool_calls: list[NormalizedVoiceToolCall] = field(default_factory=list)
    raw_type: str | None = None
