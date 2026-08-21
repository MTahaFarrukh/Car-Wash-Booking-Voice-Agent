"""Abstract voice provider interface (Phase 8 / 8.1)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.voice.normalized import NormalizedVoiceEvent, NormalizedVoiceToolCall


class VoiceProvider(ABC):
    """Replaceable telephony / realtime voice backend."""

    name: str = "base"

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True when credentials required by this provider are present."""

    @abstractmethod
    def create_session(
        self,
        *,
        call_id: str,
        caller_phone: str | None = None,
        participant_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Create or attach a provider session for an inbound call.

        Returns provider metadata only (tokens, URLs). Never returns secrets
        that belong in environment configuration.
        """

    @abstractmethod
    def supports_barge_in(self) -> bool:
        """Whether the provider natively supports caller interruptions."""

    def verify_webhook(
        self,
        *,
        headers: dict[str, str],
        body: bytes,
    ) -> bool:
        """
        Verify an inbound provider webhook.

        Default: reject. Concrete providers override with their auth scheme.
        """
        return False

    def parse_webhook(self, payload: dict[str, Any]) -> list[NormalizedVoiceEvent]:
        """
        Parse a provider-native webhook body into normalized events.

        Default: no events. Providers must not leak raw payloads to domain code.
        """
        return []

    def normalize_tool_calls(self, payload: dict[str, Any]) -> list[NormalizedVoiceToolCall]:
        """Extract normalized tool calls from a provider-native payload."""
        return []

    def format_tool_results(
        self,
        results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Format Phase 5 tool execution results into the provider's response shape.

        `results` items: {id, name, result (JSON-serializable), presentation?}
        """
        return {"results": results}
