"""In-memory conversation state for WhatsApp sessions."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, time
from typing import Any


@dataclass
class ConversationState:
    sender_id: str
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
    cached_services: list[dict[str, Any]] = field(default_factory=list)
    cached_vehicles: list[dict[str, Any]] = field(default_factory=list)
    cached_active_bookings: list[dict[str, Any]] = field(default_factory=list)
    # Short LLM chat history (role/content only; no secrets).
    message_history: list[dict[str, str]] = field(default_factory=list)


class ConversationStateStore:
    """Process-local store keyed by WhatsApp sender ID."""

    def __init__(self) -> None:
        self._states: dict[str, ConversationState] = {}

    def get(self, sender_id: str) -> ConversationState:
        if sender_id not in self._states:
            self._states[sender_id] = ConversationState(sender_id=sender_id)
        return self._states[sender_id]

    def reset(self, sender_id: str) -> None:
        self._states.pop(sender_id, None)


# Shared store for the running application process.
conversation_state_store = ConversationStateStore()
