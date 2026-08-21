"""Uplift AI Realtime Assistants adapter (Phase 8 / 8.1)."""

from __future__ import annotations

import hmac
import json
import logging
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.voice.base import VoiceProvider
from app.voice.normalized import NormalizedVoiceEvent, NormalizedVoiceToolCall

logger = logging.getLogger(__name__)

UPLIFT_API_BASE = "https://api.upliftai.org/v1"


class UpliftVoiceProvider(VoiceProvider):
    """
    Adapter for Uplift Realtime Assistants.

    Documented flow (https://docs.upliftai.org):
    - createSession / createPublicSession for WebRTC connection tokens
    - Custom tools run on the client via RPC (not a documented PSTN webhook)

    Sparkle therefore exposes `/api/voice/uplift/webhook` for *our* secured
    event envelope (and tool proxies), authenticated with the shared secret —
    not an invented Uplift server-event schema.
    """

    name = "uplift"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def is_configured(self) -> bool:
        return bool(
            (self.settings.uplift_api_key or "").strip()
            and (self.settings.uplift_agent_id or "").strip()
        )

    def create_session(
        self,
        *,
        call_id: str,
        caller_phone: str | None = None,
        participant_name: str | None = None,
    ) -> dict[str, Any]:
        if not self.is_configured():
            return {
                "provider": self.name,
                "call_id": call_id,
                "configured": False,
                "detail": "UPLIFT_API_KEY and UPLIFT_AGENT_ID are required",
            }

        assistant_id = self.settings.uplift_agent_id.strip()
        url = f"{UPLIFT_API_BASE}/realtime-assistants/{assistant_id}/createSession"
        headers = {
            "Authorization": f"Bearer {self.settings.uplift_api_key.strip()}",
            "Content-Type": "application/json",
        }
        body = {
            "participantName": participant_name or caller_phone or "Caller",
        }
        timeout = self.settings.llm_timeout_seconds
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(url, headers=headers, json=body)
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:
            logger.warning(
                "uplift_create_session_failed call_id=%s error=%s",
                call_id,
                type(exc).__name__,
            )
            return {
                "provider": self.name,
                "call_id": call_id,
                "configured": True,
                "error": "Failed to create Uplift session",
            }

        return {
            "provider": self.name,
            "call_id": call_id,
            "assistant_id": assistant_id,
            "caller_phone": caller_phone,
            "session": payload,
            "barge_in": True,
            "notes": (
                "Register Phase 5 tools in the Uplift room client and proxy handlers "
                "to POST /api/voice/tools/execute or /api/voice/uplift/webhook."
            ),
        }

    def supports_barge_in(self) -> bool:
        return True

    def verify_webhook(self, *, headers: dict[str, str], body: bytes) -> bool:
        """
        Uplift tools are client-side RPC. Sparkle authenticates our uplift ingress
        with the shared voice / uplift webhook secret (Bearer or X-Voice-Webhook-Secret).
        """
        expected = (
            (self.settings.uplift_webhook_secret or "").strip()
            or (self.settings.voice_webhook_secret or "").strip()
        )
        if not expected:
            return False
        normalized = {k.lower(): v for k, v in headers.items()}
        auth = normalized.get("authorization", "")
        if auth.lower().startswith("bearer "):
            if hmac.compare_digest(auth[7:].strip(), expected):
                return True
        for header in ("x-voice-webhook-secret", "x-uplift-webhook-secret"):
            value = normalized.get(header, "")
            if value and hmac.compare_digest(value, expected):
                return True
        return False

    def parse_webhook(self, payload: dict[str, Any]) -> list[NormalizedVoiceEvent]:
        """
        Parse Sparkle-canonical uplift ingress (not an invented Uplift PSTN schema).

        Accepted shapes:
        - { "event_type", "call_id", "payload": {...} }
        - { "type": "tool.execute", "call_id", "name", "arguments" }
        """
        event_type = str(payload.get("event_type") or payload.get("type") or "").strip()
        call_id = str(payload.get("call_id") or "").strip()
        if not call_id:
            return []

        body = payload.get("payload") if isinstance(payload.get("payload"), dict) else payload
        phone = None
        if isinstance(body.get("caller_phone"), str):
            phone = body["caller_phone"]

        if event_type in {"call.started", "call.ended", "call.turn", "tool.execute", "user.interrupted"}:
            tool_calls: list[NormalizedVoiceToolCall] = []
            if event_type == "tool.execute":
                tool_calls = self.normalize_tool_calls(payload)
            return [
                NormalizedVoiceEvent(
                    event_type=event_type,  # type: ignore[arg-type]
                    call_id=call_id,
                    provider=self.name,
                    caller_phone=phone or (
                        body.get("caller_phone") if isinstance(body.get("caller_phone"), str) else None
                    ),
                    text=body.get("text") if isinstance(body.get("text"), str) else None,
                    interrupted=bool(body.get("interrupted", event_type == "user.interrupted")),
                    duration_seconds=body.get("duration_seconds")
                    if isinstance(body.get("duration_seconds"), int)
                    else None,
                    outcome=body.get("outcome") if isinstance(body.get("outcome"), str) else None,
                    tool_calls=tool_calls,
                    raw_type=event_type,
                )
            ]

        return [
            NormalizedVoiceEvent(
                event_type="ignored",
                call_id=call_id,
                provider=self.name,
                raw_type=event_type or "unknown",
            )
        ]

    def normalize_tool_calls(self, payload: dict[str, Any]) -> list[NormalizedVoiceToolCall]:
        body = payload.get("payload") if isinstance(payload.get("payload"), dict) else payload
        # Single tool
        name = body.get("name") or payload.get("name")
        if isinstance(name, str) and name.strip():
            args = body.get("arguments") or payload.get("arguments") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            if not isinstance(args, dict):
                args = {}
            tool_id = str(body.get("tool_call_id") or payload.get("tool_call_id") or name)
            return [NormalizedVoiceToolCall(id=tool_id, name=name.strip(), arguments=args)]

        # Batch
        items = body.get("tool_calls") or payload.get("tool_calls") or []
        calls: list[NormalizedVoiceToolCall] = []
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                n = str(item.get("name") or "").strip()
                if not n:
                    continue
                args = item.get("arguments") or {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                if not isinstance(args, dict):
                    args = {}
                calls.append(
                    NormalizedVoiceToolCall(
                        id=str(item.get("id") or n),
                        name=n,
                        arguments=args,
                    )
                )
        return calls

    def format_tool_results(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        # Match Uplift client tool response recommendation.
        if len(results) == 1:
            item = results[0]
            return {
                "result": item.get("result"),
                "presentationInstructions": item.get("presentation"),
            }
        return {
            "results": [
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "result": item.get("result"),
                    "presentationInstructions": item.get("presentation"),
                }
                for item in results
            ]
        }
