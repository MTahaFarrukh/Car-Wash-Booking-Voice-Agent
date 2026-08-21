"""In-memory call session state for the voice channel."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, time
from typing import Any


@dataclass
class CallSessionState:
    call_id: str
    provider: str = "fake"
    customer_id: uuid.UUID | None = None
    customer_name: str | None = None
    phone: str | None = None
    selected_vehicle_id: uuid.UUID | None = None
    selected_vehicle_label: str | None = None
    selected_service_id: uuid.UUID | None = None
    selected_service_name: str | None = None
    requested_date: date | None = None
    requested_time: time | None = None
    pending_intent: str | None = None
    target_booking_id: uuid.UUID | None = None
    awaiting_confirmation: bool = False
    last_booking_id: uuid.UUID | None = None
    outcome_hint: str | None = None
    cached_services: list[dict[str, Any]] = field(default_factory=list)
    cached_vehicles: list[dict[str, Any]] = field(default_factory=list)
    cached_active_bookings: list[dict[str, Any]] = field(default_factory=list)
    message_history: list[dict[str, str]] = field(default_factory=list)


class CallSessionStore:
    """Process-local store keyed by provider call ID."""

    def __init__(self) -> None:
        self._states: dict[str, CallSessionState] = {}

    def get(self, call_id: str, *, provider: str = "fake") -> CallSessionState:
        if call_id not in self._states:
            self._states[call_id] = CallSessionState(call_id=call_id, provider=provider)
        return self._states[call_id]

    def reset(self, call_id: str) -> None:
        self._states.pop(call_id, None)

    def clear(self) -> None:
        self._states.clear()


call_session_store = CallSessionStore()
