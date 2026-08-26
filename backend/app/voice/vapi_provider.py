"""VAPI voice provider adapter (Phase 8.1)."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.voice.base import VoiceProvider
from app.voice.normalized import NormalizedVoiceEvent, NormalizedVoiceToolCall

logger = logging.getLogger(__name__)

VAPI_API_BASE = "https://api.vapi.ai"


class VapiVoiceProvider(VoiceProvider):
    """
    Adapter for VAPI Server URL / tool-calls webhooks.

    Documented contract (https://docs.vapi.ai/server-url/events):
    - POST body: { "message": { "type": "...", "call": {...}, ... } }
    - tool-calls expect { "results": [ { "name", "toolCallId", "result" } ] }
    - Auth via Custom Credentials: Bearer token and/or HMAC (configurable header)

    Provider-specific payloads stay inside this adapter.
    """

    name = "vapi"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def is_configured(self) -> bool:
        return bool(
            (self.settings.vapi_api_key or "").strip()
            and (self.settings.vapi_assistant_id or "").strip()
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
                "detail": "VAPI_API_KEY and VAPI_ASSISTANT_ID are required",
            }

        # Inbound VAPI calls are driven by Server URL webhooks. We do not place
        # an outbound call unless explicitly requested via outbound helper.
        return {
            "provider": self.name,
            "call_id": call_id,
            "configured": True,
            "assistant_id": self.settings.vapi_assistant_id.strip(),
            "caller_phone": caller_phone,
            "participant_name": participant_name,
            "barge_in": True,
            "server_url_path": "/api/voice/vapi/webhook",
            "notes": (
                "Configure the VAPI assistant Server URL to POST /api/voice/vapi/webhook "
                "and set VAPI_WEBHOOK_SECRET (Bearer / X-Vapi-Secret)."
            ),
        }

    def supports_barge_in(self) -> bool:
        return True

    def verify_webhook(self, *, headers: dict[str, str], body: bytes) -> bool:
        """
        Verify VAPI → Sparkle auth.

        Supports:
        - Authorization: Bearer <VAPI_WEBHOOK_SECRET>
        - X-Vapi-Secret: <VAPI_WEBHOOK_SECRET> (legacy)
        - Optional HMAC when VAPI_WEBHOOK_SECRET is set and x-signature / configured header present
        """
        secret = (self.settings.vapi_webhook_secret or "").strip()
        if not secret:
            return False

        normalized = {k.lower(): v for k, v in headers.items()}

        auth = normalized.get("authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
            if hmac.compare_digest(token, secret):
                return True

        legacy = normalized.get("x-vapi-secret", "")
        if legacy and hmac.compare_digest(legacy, secret):
            return True

        # Optional HMAC (header name configurable; default x-signature / x-vapi-signature)
        sig_header = (
            normalized.get("x-vapi-signature")
            or normalized.get("x-signature")
            or ""
        )
        if sig_header:
            digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
            # Accept raw hex or sha256=<hex>
            candidate = sig_header.removeprefix("sha256=").strip()
            if hmac.compare_digest(candidate, digest):
                return True

        return False

    def parse_webhook(self, payload: dict[str, Any]) -> list[NormalizedVoiceEvent]:
        message = payload.get("message")
        if not isinstance(message, dict):
            return []

        msg_type = str(message.get("type") or "")
        call = message.get("call") if isinstance(message.get("call"), dict) else {}
        call_id = str(call.get("id") or message.get("callId") or "").strip()
        if not call_id:
            return []

        phone = self._extract_phone(message, call)
        events: list[NormalizedVoiceEvent] = []

        if msg_type == "status-update":
            status = str(message.get("status") or "")
            if status == "in-progress":
                events.append(
                    NormalizedVoiceEvent(
                        event_type="call.started",
                        call_id=call_id,
                        provider=self.name,
                        caller_phone=phone,
                        raw_type=msg_type,
                    )
                )
            elif status == "ended":
                events.append(
                    NormalizedVoiceEvent(
                        event_type="call.ended",
                        call_id=call_id,
                        provider=self.name,
                        caller_phone=phone,
                        raw_type=msg_type,
                    )
                )
            else:
                events.append(
                    NormalizedVoiceEvent(
                        event_type="ignored",
                        call_id=call_id,
                        provider=self.name,
                        raw_type=msg_type,
                    )
                )
            return events

        if msg_type == "end-of-call-report":
            duration = None
            if isinstance(call.get("endedAt"), str) and isinstance(call.get("startedAt"), str):
                duration = None  # leave to service if timestamps need parsing
            artifact = message.get("artifact") if isinstance(message.get("artifact"), dict) else {}
            # Prefer explicit duration fields when present
            for key in ("durationSeconds", "duration", "endedReason"):
                if key == "endedReason":
                    continue
                if isinstance(message.get(key), (int, float)):
                    duration = int(message[key])
                    break
                if isinstance(call.get(key), (int, float)):
                    duration = int(call[key])
                    break
            if duration is None and isinstance(artifact.get("durationSeconds"), (int, float)):
                duration = int(artifact["durationSeconds"])
            events.append(
                NormalizedVoiceEvent(
                    event_type="call.ended",
                    call_id=call_id,
                    provider=self.name,
                    caller_phone=phone,
                    duration_seconds=duration,
                    raw_type=msg_type,
                )
            )
            return events

        if msg_type == "tool-calls":
            tool_calls = self.normalize_tool_calls(payload)
            events.append(
                NormalizedVoiceEvent(
                    event_type="tool.execute",
                    call_id=call_id,
                    provider=self.name,
                    caller_phone=phone,
                    tool_calls=tool_calls,
                    raw_type=msg_type,
                )
            )
            return events

        if msg_type == "user-interrupted":
            events.append(
                NormalizedVoiceEvent(
                    event_type="user.interrupted",
                    call_id=call_id,
                    provider=self.name,
                    caller_phone=phone,
                    interrupted=True,
                    raw_type=msg_type,
                )
            )
            return events

        if msg_type == "transcript":
            if str(message.get("transcriptType") or "") == "final" and message.get("role") == "user":
                text = str(message.get("transcript") or "").strip()
                if text:
                    events.append(
                        NormalizedVoiceEvent(
                            event_type="call.turn",
                            call_id=call_id,
                            provider=self.name,
                            caller_phone=phone,
                            text=text,
                            raw_type=msg_type,
                        )
                    )
                    return events
            events.append(
                NormalizedVoiceEvent(
                    event_type="ignored",
                    call_id=call_id,
                    provider=self.name,
                    raw_type=msg_type,
                )
            )
            return events

        if msg_type == "assistant-request":
            # Handled specially by the router (returns assistantId); mark as ignored here.
            events.append(
                NormalizedVoiceEvent(
                    event_type="ignored",
                    call_id=call_id,
                    provider=self.name,
                    caller_phone=phone,
                    raw_type=msg_type,
                )
            )
            return events

        events.append(
            NormalizedVoiceEvent(
                event_type="ignored",
                call_id=call_id,
                provider=self.name,
                raw_type=msg_type,
            )
        )
        return events

    def normalize_tool_calls(self, payload: dict[str, Any]) -> list[NormalizedVoiceToolCall]:
        message = payload.get("message") if isinstance(payload.get("message"), dict) else payload
        calls: list[NormalizedVoiceToolCall] = []
        seen: set[str] = set()

        def _append(call_id: Any, name: Any, params: Any) -> None:
            cid = str(call_id or "").strip()
            n = str(name or "").strip()
            if isinstance(params, str):
                try:
                    params = json.loads(params)
                except json.JSONDecodeError:
                    params = {}
            if not isinstance(params, dict):
                params = {}
            if not cid or not n or cid in seen:
                return
            seen.add(cid)
            calls.append(NormalizedVoiceToolCall(id=cid, name=n, arguments=params))

        def _from_item(item: dict[str, Any], *, fallback_name: Any = None) -> None:
            function = item.get("function") if isinstance(item.get("function"), dict) else {}
            _append(
                item.get("id"),
                item.get("name") or function.get("name") or fallback_name,
                item.get("parameters")
                or item.get("arguments")
                or function.get("arguments")
                or function.get("parameters"),
            )

        for key in ("toolCallList", "toolCalls", "tool_calls"):
            items = message.get(key)
            if not isinstance(items, list):
                continue
            for item in items:
                if isinstance(item, dict):
                    _from_item(item)

        bundled = message.get("toolWithToolCallList")
        if isinstance(bundled, list):
            for item in bundled:
                if not isinstance(item, dict):
                    continue
                tool_call = item.get("toolCall") if isinstance(item.get("toolCall"), dict) else {}
                function = tool_call.get("function") if isinstance(tool_call.get("function"), dict) else {}
                _append(
                    tool_call.get("id") or item.get("id"),
                    item.get("name") or tool_call.get("name") or function.get("name"),
                    tool_call.get("parameters")
                    or tool_call.get("arguments")
                    or function.get("arguments")
                    or function.get("parameters")
                    or item.get("parameters"),
                )

        # Top-level OpenAI-style (some custom tool posts)
        top_calls = payload.get("toolCalls") if isinstance(payload.get("toolCalls"), list) else []
        for item in top_calls:
            if isinstance(item, dict):
                _from_item(item)

        return calls

    def extract_tool_call_ids(self, payload: dict[str, Any]) -> list[str]:
        """Best-effort ids for fallback responses when parsing fails."""
        ids: list[str] = []
        seen: set[str] = set()

        def _add(value: Any) -> None:
            cid = str(value or "").strip()
            if cid and cid not in seen:
                seen.add(cid)
                ids.append(cid)

        message = payload.get("message") if isinstance(payload.get("message"), dict) else payload
        for key in ("toolCallList", "toolCalls", "tool_calls"):
            items = message.get(key)
            if not isinstance(items, list):
                continue
            for item in items:
                if isinstance(item, dict):
                    _add(item.get("id"))
        bundled = message.get("toolWithToolCallList")
        if isinstance(bundled, list):
            for item in bundled:
                if not isinstance(item, dict):
                    continue
                tool_call = item.get("toolCall") if isinstance(item.get("toolCall"), dict) else {}
                _add(tool_call.get("id") or item.get("id"))
        return ids

    def format_tool_results(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        """
        VAPI requires a `result` string for every toolCallId:
        { "results": [ { "toolCallId": "<exact id>", "result": "<single-line string>" } ] }

        Using only an `error` key (without `result`) triggers "No result returned".
        """
        formatted = []
        for item in results:
            tool_call_id = str(item.get("id") or item.get("toolCallId") or "").strip()
            presentation = item.get("presentation")
            result_payload = item.get("result")
            success = True
            if isinstance(result_payload, dict):
                success = bool(result_payload.get("success", True))
            if presentation:
                text = str(presentation).replace("\n", " ").strip()
            elif isinstance(result_payload, dict):
                if success:
                    text = "Booking saved successfully."
                else:
                    err = result_payload.get("error") or {}
                    text = str(err.get("message") or "Tool failed").replace("\n", " ").strip()
            else:
                text = str(result_payload or "").replace("\n", " ").strip() or "OK"
            if not text:
                text = "OK"
            formatted.append({"toolCallId": tool_call_id, "result": text})
        return {"results": formatted}

    def assistant_request_response(self) -> dict[str, Any]:
        assistant_id = (self.settings.vapi_assistant_id or "").strip()
        if assistant_id:
            return {"assistantId": assistant_id}
        return {"error": "Voice assistant is not configured."}

    def create_outbound_call(
        self,
        *,
        customer_number: str,
        assistant_id: str | None = None,
    ) -> dict[str, Any]:
        """Optional helper — only used when explicitly invoked with credentials."""
        if not (self.settings.vapi_api_key or "").strip():
            return {"error": "VAPI_API_KEY is required"}
        aid = (assistant_id or self.settings.vapi_assistant_id or "").strip()
        if not aid:
            return {"error": "VAPI_ASSISTANT_ID is required"}
        url = f"{VAPI_API_BASE}/call/phone"
        headers = {
            "Authorization": f"Bearer {self.settings.vapi_api_key.strip()}",
            "Content-Type": "application/json",
        }
        body = {
            "assistantId": aid,
            "customer": {"number": customer_number},
        }
        try:
            with httpx.Client(timeout=self.settings.llm_timeout_seconds) as client:
                response = client.post(url, headers=headers, json=body)
            response.raise_for_status()
            return {"provider": self.name, "call": response.json()}
        except httpx.HTTPError as exc:
            logger.warning("vapi_outbound_failed error=%s", type(exc).__name__)
            return {"provider": self.name, "error": "Failed to create VAPI call"}

    @staticmethod
    def _extract_phone(message: dict[str, Any], call: dict[str, Any]) -> str | None:
        for container in (
            call.get("customer") if isinstance(call.get("customer"), dict) else None,
            message.get("customer") if isinstance(message.get("customer"), dict) else None,
            call.get("metadata") if isinstance(call.get("metadata"), dict) else None,
            message.get("metadata") if isinstance(message.get("metadata"), dict) else None,
            call.get("assistantOverrides") if isinstance(call.get("assistantOverrides"), dict) else None,
            (
                (call.get("assistantOverrides") or {}).get("variableValues")
                if isinstance((call.get("assistantOverrides") or {}).get("variableValues"), dict)
                else None
            ),
            call,
            message,
        ):
            if not container:
                continue
            for key in (
                "number",
                "phoneNumber",
                "phone",
                "customerPhone",
                "customer_phone",
                "callerPhone",
            ):
                value = container.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        phone_number = message.get("phoneNumber")
        if isinstance(phone_number, dict):
            number = phone_number.get("number")
            if isinstance(number, str) and number.strip():
                return number.strip()
        return None
