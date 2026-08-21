"""Fake voice provider for automated tests (no network)."""

from __future__ import annotations

import hmac
from typing import Any

from app.voice.base import VoiceProvider
from app.voice.normalized import NormalizedVoiceEvent, NormalizedVoiceToolCall


class FakeVoiceProvider(VoiceProvider):
    """Deterministic in-process provider used by pytest."""

    name = "fake"

    def __init__(self, *, configured: bool = True, webhook_secret: str = "fake-secret") -> None:
        self._configured = configured
        self.webhook_secret = webhook_secret
        self.sessions: list[dict[str, Any]] = []

    def is_configured(self) -> bool:
        return self._configured

    def create_session(
        self,
        *,
        call_id: str,
        caller_phone: str | None = None,
        participant_name: str | None = None,
    ) -> dict[str, Any]:
        session = {
            "provider": self.name,
            "call_id": call_id,
            "caller_phone": caller_phone,
            "participant_name": participant_name,
            "session_token": f"fake-token-{call_id}",
            "barge_in": True,
        }
        self.sessions.append(session)
        return session

    def supports_barge_in(self) -> bool:
        return True

    def verify_webhook(self, *, headers: dict[str, str], body: bytes) -> bool:
        normalized = {k.lower(): v for k, v in headers.items()}
        secret = normalized.get("x-voice-webhook-secret", "")
        return bool(secret) and hmac.compare_digest(secret, self.webhook_secret)

    def parse_webhook(self, payload: dict[str, Any]) -> list[NormalizedVoiceEvent]:
        event_type = str(payload.get("event_type") or "ignored")
        call_id = str(payload.get("call_id") or "")
        if not call_id:
            return []
        body = payload.get("payload") if isinstance(payload.get("payload"), dict) else payload
        return [
            NormalizedVoiceEvent(
                event_type=event_type if event_type in {
                    "call.started",
                    "call.ended",
                    "call.turn",
                    "tool.execute",
                    "user.interrupted",
                    "ignored",
                } else "ignored",  # type: ignore[arg-type]
                call_id=call_id,
                provider=self.name,
                caller_phone=body.get("caller_phone") if isinstance(body.get("caller_phone"), str) else None,
                text=body.get("text") if isinstance(body.get("text"), str) else None,
                interrupted=bool(body.get("interrupted", False)),
                tool_calls=self.normalize_tool_calls(payload) if event_type == "tool.execute" else [],
                raw_type=event_type,
            )
        ]

    def normalize_tool_calls(self, payload: dict[str, Any]) -> list[NormalizedVoiceToolCall]:
        body = payload.get("payload") if isinstance(payload.get("payload"), dict) else payload
        name = body.get("name")
        if not isinstance(name, str):
            return []
        args = body.get("arguments") if isinstance(body.get("arguments"), dict) else {}
        return [NormalizedVoiceToolCall(id=str(body.get("id") or name), name=name, arguments=args)]
