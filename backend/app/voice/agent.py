"""LLM-powered voice conversation agent (Phase 8)."""

from __future__ import annotations

import json
import logging
import re
import time as time_module
import uuid
from datetime import date

from app.agent.service import AgentIntegrationService
from app.core.config import Settings, get_settings
from app.llm.base import LLMProvider
from app.llm.errors import LLMProviderError
from app.llm.schemas import LLMMessage, LLMToolCall
from app.models.booking import BookingSource, BookingStatus
from app.schemas.agent import ServicesListInput, VehicleLookupInput
from app.services.booking_service import BookingService
from app.voice.prompts import build_voice_system_prompt
from app.voice.state import CallSessionState
from app.whatsapp.tool_executor import Phase5ToolExecutor, get_llm_tool_specs

logger = logging.getLogger(__name__)

ACTIVE_BOOKING_STATUSES = {BookingStatus.PENDING, BookingStatus.CONFIRMED}
FALLBACK_REPLY = "Sorry, I'm having a little trouble right now. Could you say that again?"
HISTORY_LIMIT = 10
GREETING = (
    "Hi, thanks for calling Sparkle Car Wash. "
    "I can help you book, reschedule, or cancel a wash. How can I help?"
)


class VoiceConversationAgent:
    """Spoken orchestrator that calls Phase 5 tools via an LLM provider."""

    def __init__(
        self,
        agent: AgentIntegrationService,
        booking_service: BookingService,
        llm: LLMProvider,
        settings: Settings | None = None,
    ) -> None:
        self.agent = agent
        self.booking_service = booking_service
        self.llm = llm
        self.settings = settings or get_settings()
        self.executor = Phase5ToolExecutor(agent, booking_source=BookingSource.VOICE)
        self.tools = get_llm_tool_specs()

    def greeting(self) -> str:
        return GREETING

    def handle_turn(self, state: CallSessionState, text: str, *, interrupted: bool = False) -> str:
        cleaned = (text or "").strip()
        if not cleaned:
            return "I didn't catch that. Could you repeat it?"

        if interrupted and state.message_history:
            # Drop trailing unfinished assistant utterance on barge-in.
            if state.message_history and state.message_history[-1].get("role") == "assistant":
                state.message_history.pop()

        self._refresh_context(state)
        messages = self._build_messages(state, cleaned)

        started = time_module.perf_counter()
        tool_calls_used = 0
        max_calls = max(1, self.settings.llm_max_tool_calls)

        try:
            for _ in range(max_calls):
                completion = self.llm.complete_with_tools(
                    messages,
                    self.tools,
                    temperature=self.settings.llm_temperature,
                    max_tokens=min(self.settings.llm_max_tokens, 400),
                )

                if completion.has_tool_calls:
                    messages.append(
                        LLMMessage(
                            role="assistant",
                            content=completion.content,
                            tool_calls=completion.tool_calls,
                            provider_parts=completion.provider_parts,
                        )
                    )
                    for call in completion.tool_calls:
                        tool_calls_used += 1
                        if tool_calls_used > max_calls:
                            logger.warning(
                                "voice_tool_loop_guard call_id=%s calls=%s",
                                state.call_id,
                                tool_calls_used,
                            )
                            reply = FALLBACK_REPLY
                            self._remember(state, cleaned, reply)
                            return reply
                        tool_payload = self._run_tool(call, state)
                        messages.append(
                            LLMMessage(
                                role="tool",
                                tool_call_id=call.id,
                                name=call.name,
                                content=tool_payload,
                            )
                        )
                    continue

                reply = (completion.content or "").strip() or FALLBACK_REPLY
                reply = self._sanitize_spoken_reply(reply)
                elapsed_ms = int((time_module.perf_counter() - started) * 1000)
                logger.info(
                    "voice_reply call_id=%s tools=%s latency_ms=%s",
                    state.call_id,
                    tool_calls_used,
                    elapsed_ms,
                )
                self._remember(state, cleaned, reply)
                return reply

            logger.warning("voice_tool_loop_exhausted call_id=%s", state.call_id)
            reply = FALLBACK_REPLY
            self._remember(state, cleaned, reply)
            return reply
        except LLMProviderError:
            logger.exception("voice_llm_provider_failed call_id=%s", state.call_id)
            reply = FALLBACK_REPLY
            self._remember(state, cleaned, reply)
            return reply
        except Exception:
            logger.exception("voice_agent_failed call_id=%s", state.call_id)
            reply = FALLBACK_REPLY
            self._remember(state, cleaned, reply)
            return reply

    def execute_tool(
        self,
        state: CallSessionState,
        name: str,
        arguments: dict,
    ) -> tuple[dict, str | None]:
        """Direct Phase 5 tool execution for provider-proxied tool RPC."""
        from app.llm.schemas import LLMToolCall

        from app.voice.tool_aliases import execute_save_booking, normalize_tool_name

        resolved = normalize_tool_name(name)
        if resolved == "save_booking":
            return execute_save_booking(self.agent, state, arguments or {})

        call = LLMToolCall(id=str(uuid.uuid4()), name=resolved, arguments=arguments or {})
        raw = self._run_tool(call, state)
        payload = json.loads(raw)
        spoken = None
        if payload.get("success") and resolved == "create_booking":
            spoken = "Your booking is confirmed."
            state.outcome_hint = "booking_created"
        elif payload.get("success") and resolved == "cancel_booking":
            spoken = "Your booking has been cancelled."
            state.outcome_hint = "cancelled"
        elif not payload.get("success"):
            error = (payload.get("error") or {}).get("error_code")
            spoken = self._spoken_error(error)
        return payload, spoken

    def _run_tool(self, call: LLMToolCall, state: CallSessionState) -> str:
        logger.info("voice_tool_call call_id=%s name=%s", state.call_id, call.name)
        # ConversationState-compatible duck typing for Phase5ToolExecutor.
        result = self.executor.execute(call.name, call.arguments, state)  # type: ignore[arg-type]
        success = result.success
        error_code = result.error.error_code if result.error else None
        logger.info(
            "voice_tool_result call_id=%s name=%s success=%s error=%s",
            state.call_id,
            call.name,
            success,
            error_code,
        )
        if success and call.name == "create_booking" and result.data:
            booking = result.data.get("booking") or {}
            if booking.get("booking_id"):
                state.last_booking_id = uuid.UUID(str(booking["booking_id"]))
                state.outcome_hint = "booking_created"
        if success and call.name == "cancel_booking":
            state.outcome_hint = "cancelled"
        if success and call.name == "reschedule_booking":
            state.outcome_hint = "booking_created"
        if call.name in {"create_vehicle", "create_booking", "cancel_booking", "reschedule_booking"}:
            self._refresh_context(state)
        return result.model_dump_json()

    def _refresh_context(self, state: CallSessionState) -> None:
        services = self.agent.list_services(ServicesListInput(active_only=True))
        if services.success and services.data:
            state.cached_services = services.data.get("services", [])

        if state.customer_id:
            vehicles = self.agent.get_customer_vehicles(VehicleLookupInput(customer_id=state.customer_id))
            if vehicles.success and vehicles.data:
                state.cached_vehicles = vehicles.data.get("vehicles", [])
            state.cached_active_bookings = self._load_active_bookings(state.customer_id)

    def _load_active_bookings(self, customer_id: uuid.UUID) -> list[dict]:
        bookings = self.booking_service.get_customer_bookings(customer_id)
        active = []
        for booking in bookings:
            if booking.status not in ACTIVE_BOOKING_STATUSES:
                continue
            active.append(
                {
                    "booking_id": str(booking.id),
                    "booking_date": booking.booking_date.isoformat(),
                    "booking_time": booking.booking_time.isoformat(),
                    "service_id": str(booking.service_id),
                    "service_name": booking.service.name if booking.service else "Service",
                    "vehicle_label": (
                        f"{booking.vehicle.make} {booking.vehicle.model}" if booking.vehicle else "Vehicle"
                    ),
                    "status": booking.status.value,
                }
            )
        return active

    def _build_messages(self, state: CallSessionState, text: str) -> list[LLMMessage]:
        messages = [
            LLMMessage(role="system", content=build_voice_system_prompt(today=date.today())),
            LLMMessage(role="system", content=self._session_context(state)),
        ]
        for item in state.message_history[-HISTORY_LIMIT:]:
            role = item.get("role")
            content = item.get("content")
            if role in {"user", "assistant"} and content:
                messages.append(LLMMessage(role=role, content=content))  # type: ignore[arg-type]
        messages.append(LLMMessage(role="user", content=text))
        return messages

    def _session_context(self, state: CallSessionState) -> str:
        payload = {
            "channel": "voice",
            "call_id": state.call_id,
            "customer_id": str(state.customer_id) if state.customer_id else None,
            "customer_name": state.customer_name,
            "phone": state.phone,
            "selected_vehicle_id": str(state.selected_vehicle_id) if state.selected_vehicle_id else None,
            "selected_vehicle_label": state.selected_vehicle_label,
            "selected_service_id": str(state.selected_service_id) if state.selected_service_id else None,
            "selected_service_name": state.selected_service_name,
            "requested_date": state.requested_date.isoformat() if state.requested_date else None,
            "requested_time": state.requested_time.isoformat() if state.requested_time else None,
            "pending_intent": state.pending_intent,
            "target_booking_id": str(state.target_booking_id) if state.target_booking_id else None,
            "vehicles": state.cached_vehicles,
            "services": [
                {
                    "service_id": item.get("service_id"),
                    "name": item.get("name"),
                    "duration_minutes": item.get("duration_minutes"),
                    "price": item.get("price"),
                }
                for item in state.cached_services
            ],
            "active_bookings": state.cached_active_bookings,
        }
        return (
            "SESSION CONTEXT (source of truth for IDs; never invent missing IDs; "
            "never speak raw IDs to the caller):\n"
            + json.dumps(payload, default=str)
        )

    @staticmethod
    def _remember(state: CallSessionState, user_text: str, assistant_text: str) -> None:
        state.message_history.append({"role": "user", "content": user_text})
        state.message_history.append({"role": "assistant", "content": assistant_text})
        if len(state.message_history) > HISTORY_LIMIT * 2:
            state.message_history = state.message_history[-(HISTORY_LIMIT * 2) :]

    @staticmethod
    def _sanitize_spoken_reply(reply: str) -> str:
        text = reply.strip()
        text = re.sub(r"[*_`#]+", "", text)
        text = re.sub(r"^\s*[-•]\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"\s+\n", " ", text)
        text = re.sub(r"\n+", " ", text)
        text = re.sub(r"\s{2,}", " ", text).strip()
        lowered = text.lower()
        blocked = ("system prompt", "api key", "database", "tool_call", "stack trace", "json")
        if any(phrase in lowered for phrase in blocked) and "booking" not in lowered:
            return (
                "I can help with car wash bookings, services, rescheduling, and cancellations. "
                "What would you like to do?"
            )
        return text

    @staticmethod
    def _spoken_error(error_code: str | None) -> str:
        mapping = {
            "SLOT_UNAVAILABLE": "That time isn't available. I can suggest other open times if you like.",
            "CUSTOMER_NOT_FOUND": "I couldn't find your account yet. May I have your name?",
            "VEHICLE_NOT_FOUND": "I don't have that vehicle on file. What car will you bring?",
            "SERVICE_NOT_FOUND": "I couldn't find that service. Would you like to hear our options?",
            "BOOKING_NOT_FOUND": "I couldn't find that booking. Can you tell me the date or service?",
            "INVALID_BOOKING_TIME": "That time doesn't look valid. What time works for you?",
            "BOOKING_ALREADY_CANCELLED": "That booking is already cancelled.",
            "DUPLICATE_REQUEST": "It looks like that booking is already in place.",
            "VALIDATION_ERROR": "I'm missing a detail. Could you repeat the service, car, date, or time?",
        }
        return mapping.get(error_code or "", "Sorry, I couldn't complete that. Could we try again?")
