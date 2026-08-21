"""Voice call orchestration: identity, turns, tools, CallLog."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.service import AgentIntegrationService
from app.core.config import Settings, get_settings
from app.llm.base import LLMProvider
from app.llm.provider import create_llm_provider
from app.models.call_log import CallLog, CallOutcome
from app.schemas.agent import CustomerLookupInput, CustomerToolInput
from app.services.booking_service import BookingService
from app.voice.agent import GREETING, VoiceConversationAgent
from app.voice.base import VoiceProvider
from app.voice.normalized import NormalizedVoiceEvent
from app.voice.provider import create_voice_provider
from app.voice.schemas import (
    VoiceCallEndRequest,
    VoiceCallEndResponse,
    VoiceCallStartRequest,
    VoiceCallStartResponse,
    VoiceToolExecuteRequest,
    VoiceToolExecuteResponse,
    VoiceTurnRequest,
    VoiceTurnResponse,
    VoiceWebhookEvent,
)
from app.voice.state import CallSessionState, call_session_store
from app.whatsapp.parser import uuid_from_string

logger = logging.getLogger(__name__)

OUTCOME_MAP = {
    "booking_created": CallOutcome.BOOKING_CREATED,
    "information_request": CallOutcome.INFORMATION_REQUEST,
    "cancelled": CallOutcome.CANCELLED,
    "no_booking": CallOutcome.NO_BOOKING,
}


class VoiceConversationService:
    """Coordinates call lifecycle, customer identity, and Phase 5 tool use."""

    def __init__(
        self,
        db: Session,
        *,
        llm: LLMProvider | None = None,
        voice_provider: VoiceProvider | None = None,
        settings: Settings | None = None,
        conversation: VoiceConversationAgent | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.agent = AgentIntegrationService(db)
        self.booking_service = BookingService(db)
        self.voice_provider = voice_provider or create_voice_provider(self.settings)
        resolved_llm = llm
        if resolved_llm is None:
            resolved_llm = create_llm_provider(self.settings)
        if conversation is not None:
            self.conversation = conversation
        elif resolved_llm is not None:
            self.conversation = VoiceConversationAgent(
                self.agent,
                self.booking_service,
                resolved_llm,
                settings=self.settings,
            )
        else:
            self.conversation = None

    def start_call(self, payload: VoiceCallStartRequest) -> VoiceCallStartResponse:
        provider_name = (payload.provider or self.voice_provider.name).strip().lower()
        state = call_session_store.get(payload.call_id, provider=provider_name)
        state.provider = provider_name
        if payload.caller_phone:
            state.phone = payload.caller_phone
            self._ensure_customer(state, payload.caller_phone, payload.caller_name)

        provider_session = self.voice_provider.create_session(
            call_id=payload.call_id,
            caller_phone=payload.caller_phone,
            participant_name=payload.caller_name or state.customer_name,
        )

        self._upsert_call_log_start(state)

        greeting = GREETING
        if self.conversation is not None:
            greeting = self.conversation.greeting()

        return VoiceCallStartResponse(
            call_id=payload.call_id,
            customer_id=state.customer_id,
            provider=provider_name,
            provider_session=provider_session,
            greeting=greeting,
        )

    def process_turn(self, payload: VoiceTurnRequest) -> VoiceTurnResponse:
        if self.conversation is None:
            return VoiceTurnResponse(
                success=False,
                call_id=payload.call_id,
                reply=(
                    "The voice agent is not configured with an LLM yet. "
                    "Please set GEMINI_API_KEY or LLM_API_KEY."
                ),
            )

        state = call_session_store.get(payload.call_id)
        if payload.caller_phone:
            state.phone = payload.caller_phone
            if state.customer_id is None:
                self._ensure_customer(state, payload.caller_phone, None)

        reply = self.conversation.handle_turn(
            state,
            payload.text,
            interrupted=payload.interrupted,
        )
        self._touch_call_log(state)

        return VoiceTurnResponse(
            call_id=payload.call_id,
            reply=reply,
            booking_id=state.last_booking_id or state.target_booking_id,
            outcome_hint=state.outcome_hint,
        )

    def execute_tool(self, payload: VoiceToolExecuteRequest) -> VoiceToolExecuteResponse:
        if self.conversation is None:
            return VoiceToolExecuteResponse(
                success=False,
                call_id=payload.call_id,
                name=payload.name,
                result={
                    "success": False,
                    "error": {
                        "error_code": "UNKNOWN_ERROR",
                        "message": "Voice LLM agent is not configured",
                    },
                },
                presentation_instructions="Sorry, voice booking is temporarily unavailable.",
            )

        state = call_session_store.get(payload.call_id)
        if payload.caller_phone:
            state.phone = payload.caller_phone
            if state.customer_id is None:
                self._ensure_customer(state, payload.caller_phone, None)

        result, spoken = self.conversation.execute_tool(state, payload.name, payload.arguments)
        self._touch_call_log(state)
        return VoiceToolExecuteResponse(
            success=bool(result.get("success")),
            call_id=payload.call_id,
            name=payload.name,
            result=result,
            presentation_instructions=spoken,
        )

    def end_call(self, payload: VoiceCallEndRequest) -> VoiceCallEndResponse:
        state = call_session_store.get(payload.call_id)
        outcome_key = payload.outcome or state.outcome_hint or "no_booking"
        if outcome_key == "booking_created" and not (state.last_booking_id or state.target_booking_id):
            outcome_key = "no_booking"
        outcome = OUTCOME_MAP.get(outcome_key, CallOutcome.NO_BOOKING)

        log = self.db.scalar(select(CallLog).where(CallLog.call_id == payload.call_id))
        ended_at = datetime.now(timezone.utc)
        duration = payload.duration_seconds
        if log is not None:
            if duration is None and log.started_at is not None:
                started = log.started_at
                if started.tzinfo is None:
                    started = started.replace(tzinfo=timezone.utc)
                duration = max(0, int((ended_at - started).total_seconds()))
            log.duration_seconds = duration
            log.outcome = outcome
            log.customer_id = state.customer_id or log.customer_id
            log.phone = state.phone or log.phone
            if state.provider:
                log.provider = state.provider
            booking_id = state.last_booking_id or state.target_booking_id
            if booking_id is not None:
                log.booking_id = booking_id
            self.db.commit()
        else:
            log = CallLog(
                call_id=payload.call_id,
                provider=state.provider,
                customer_id=state.customer_id,
                phone=state.phone,
                duration_seconds=duration,
                outcome=outcome,
                booking_id=state.last_booking_id or state.target_booking_id,
            )
            self.db.add(log)
            self.db.commit()

        call_session_store.reset(payload.call_id)
        return VoiceCallEndResponse(
            call_id=payload.call_id,
            outcome=outcome.value,
            booking_id=log.booking_id,
            duration_seconds=log.duration_seconds,
            ended_at=ended_at,
        )

    def handle_webhook(self, event: VoiceWebhookEvent) -> dict:
        """Dispatch Sparkle-canonical voice events (authenticated at the router)."""
        payload = event.payload or {}
        if event.event_type == "call.started":
            req = VoiceCallStartRequest(
                call_id=event.call_id,
                caller_phone=payload.get("caller_phone"),
                caller_name=payload.get("caller_name"),
                provider=payload.get("provider"),
            )
            return self.start_call(req).model_dump(mode="json")
        if event.event_type == "call.turn":
            text = (payload.get("text") or "").strip()
            if not text:
                return {"success": False, "detail": "Missing turn text"}
            req = VoiceTurnRequest(
                call_id=event.call_id,
                text=text,
                caller_phone=payload.get("caller_phone"),
                interrupted=bool(payload.get("interrupted", False)),
            )
            return self.process_turn(req).model_dump(mode="json")
        if event.event_type == "tool.execute":
            name = (payload.get("name") or "").strip()
            if not name:
                return {"success": False, "detail": "Missing tool name"}
            req = VoiceToolExecuteRequest(
                call_id=event.call_id,
                name=name,
                arguments=payload.get("arguments") or {},
                caller_phone=payload.get("caller_phone"),
            )
            return self.execute_tool(req).model_dump(mode="json")
        if event.event_type == "call.ended":
            req = VoiceCallEndRequest(
                call_id=event.call_id,
                duration_seconds=payload.get("duration_seconds"),
                outcome=payload.get("outcome"),
            )
            return self.end_call(req).model_dump(mode="json")
        return {"success": False, "detail": f"Unsupported event_type: {event.event_type}"}

    def handle_normalized_events(self, events: list[NormalizedVoiceEvent]) -> dict:
        """
        Apply normalized provider events through the shared voice agent.

        Returns a provider-agnostic summary. Tool-call responses are returned
        under `tool_results` for the adapter to reformat.
        """
        summary: dict = {"success": True, "handled": [], "tool_results": []}
        for event in events:
            if event.event_type == "ignored":
                summary["handled"].append({"type": event.raw_type or "ignored", "status": "ignored"})
                continue

            if event.event_type == "call.started":
                result = self.start_call(
                    VoiceCallStartRequest(
                        call_id=event.call_id,
                        caller_phone=event.caller_phone,
                        caller_name=event.caller_name,
                        provider=event.provider,
                    )
                )
                summary["handled"].append({"type": "call.started", "result": result.model_dump(mode="json")})
                continue

            if event.event_type == "call.turn":
                if not (event.text or "").strip():
                    summary["handled"].append({"type": "call.turn", "status": "empty"})
                    continue
                result = self.process_turn(
                    VoiceTurnRequest(
                        call_id=event.call_id,
                        text=event.text or "",
                        caller_phone=event.caller_phone,
                        interrupted=event.interrupted,
                    )
                )
                summary["handled"].append({"type": "call.turn", "result": result.model_dump(mode="json")})
                continue

            if event.event_type == "user.interrupted":
                state = call_session_store.get(event.call_id, provider=event.provider)
                if state.message_history and state.message_history[-1].get("role") == "assistant":
                    state.message_history.pop()
                summary["handled"].append({"type": "user.interrupted", "status": "ok"})
                continue

            if event.event_type == "tool.execute":
                for call in event.tool_calls:
                    executed = self.execute_tool(
                        VoiceToolExecuteRequest(
                            call_id=event.call_id,
                            name=call.name,
                            arguments=call.arguments,
                            caller_phone=event.caller_phone,
                        )
                    )
                    summary["tool_results"].append(
                        {
                            "id": call.id,
                            "name": call.name,
                            "result": executed.result,
                            "presentation": executed.presentation_instructions,
                        }
                    )
                summary["handled"].append({"type": "tool.execute", "count": len(event.tool_calls)})
                continue

            if event.event_type == "call.ended":
                outcome = event.outcome if event.outcome in OUTCOME_MAP else None
                result = self.end_call(
                    VoiceCallEndRequest(
                        call_id=event.call_id,
                        duration_seconds=event.duration_seconds,
                        outcome=outcome,  # type: ignore[arg-type]
                    )
                )
                summary["handled"].append({"type": "call.ended", "result": result.model_dump(mode="json")})
                continue

            summary["handled"].append({"type": event.event_type, "status": "unsupported"})
        return summary

    def _ensure_customer(
        self,
        state: CallSessionState,
        phone: str,
        caller_name: str | None,
    ) -> None:
        state.phone = phone
        lookup = self.agent.get_customer(CustomerLookupInput(phone=phone))
        if lookup.success and lookup.data:
            state.customer_id = uuid_from_string(lookup.data["customer_id"])
            state.customer_name = lookup.data.get("name")
            return

        display_name = caller_name or self._default_customer_name(phone)
        created = self.agent.find_or_create_customer(
            CustomerToolInput(name=display_name, phone=phone)
        )
        if created.success and created.data:
            state.customer_id = uuid_from_string(created.data["customer_id"])
            state.customer_name = created.data.get("name")

    @staticmethod
    def _default_customer_name(phone_number: str) -> str:
        suffix = phone_number[-4:] if len(phone_number) >= 4 else phone_number
        return f"Voice Caller {suffix}"

    def _upsert_call_log_start(self, state: CallSessionState) -> None:
        existing = self.db.scalar(select(CallLog).where(CallLog.call_id == state.call_id))
        if existing is not None:
            existing.phone = state.phone or existing.phone
            existing.customer_id = state.customer_id or existing.customer_id
            if state.provider and not existing.provider:
                existing.provider = state.provider
            self.db.commit()
            return
        log = CallLog(
            call_id=state.call_id,
            provider=state.provider,
            customer_id=state.customer_id,
            phone=state.phone,
            outcome=CallOutcome.NO_BOOKING,
        )
        self.db.add(log)
        self.db.commit()

    def _touch_call_log(self, state: CallSessionState) -> None:
        log = self.db.scalar(select(CallLog).where(CallLog.call_id == state.call_id))
        if log is None:
            self._upsert_call_log_start(state)
            log = self.db.scalar(select(CallLog).where(CallLog.call_id == state.call_id))
        if log is None:
            return
        log.customer_id = state.customer_id or log.customer_id
        log.phone = state.phone or log.phone
        if state.provider:
            log.provider = state.provider
        booking_id = state.last_booking_id or state.target_booking_id
        if booking_id is not None:
            log.booking_id = booking_id
        if state.outcome_hint == "booking_created":
            log.outcome = CallOutcome.BOOKING_CREATED
        elif state.outcome_hint == "cancelled":
            log.outcome = CallOutcome.CANCELLED
        self.db.commit()
