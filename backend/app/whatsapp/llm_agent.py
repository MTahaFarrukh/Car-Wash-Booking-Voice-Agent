"""LLM-powered WhatsApp conversation agent (Phase 7)."""

from __future__ import annotations

import json
import logging
import time as time_module
import uuid
from datetime import date

from app.agent.service import AgentIntegrationService
from app.core.config import Settings, get_settings
from app.llm.base import LLMProvider
from app.llm.errors import LLMProviderError
from app.llm.schemas import LLMMessage, LLMToolCall
from app.models.booking import BookingStatus
from app.schemas.agent import ServicesListInput, VehicleLookupInput
from app.services.booking_service import BookingService
from app.whatsapp.prompts import build_whatsapp_system_prompt
from app.whatsapp.state import ConversationState
from app.whatsapp.tool_executor import Phase5ToolExecutor, get_llm_tool_specs

logger = logging.getLogger(__name__)

ACTIVE_BOOKING_STATUSES = {BookingStatus.PENDING, BookingStatus.CONFIRMED}
FALLBACK_REPLY = "Sorry, I'm having trouble processing that right now. Please try again in a moment."
HISTORY_LIMIT = 12


class LLMConversationAgent:
    """Conversational orchestrator that calls Phase 5 tools via an LLM provider."""

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
        self.executor = Phase5ToolExecutor(agent)
        self.tools = get_llm_tool_specs()

    def handle_message(self, state: ConversationState, text: str) -> str:
        if not text.strip():
            return "Please send me a text message with what you'd like to do."

        self._refresh_context(state)
        messages = self._build_messages(state, text)

        started = time_module.perf_counter()
        tool_calls_used = 0
        max_calls = max(1, self.settings.llm_max_tool_calls)

        try:
            for _ in range(max_calls):
                completion = self.llm.complete_with_tools(
                    messages,
                    self.tools,
                    temperature=self.settings.llm_temperature,
                    max_tokens=self.settings.llm_max_tokens,
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
                                "tool_loop_guard sender=%s calls=%s",
                                state.sender_id,
                                tool_calls_used,
                            )
                            reply = FALLBACK_REPLY
                            self._remember(state, text, reply)
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
                reply = self._sanitize_customer_reply(reply)
                elapsed_ms = int((time_module.perf_counter() - started) * 1000)
                logger.info(
                    "llm_reply sender=%s tools=%s latency_ms=%s",
                    state.sender_id,
                    tool_calls_used,
                    elapsed_ms,
                )
                self._remember(state, text, reply)
                return reply

            logger.warning("tool_loop_exhausted sender=%s", state.sender_id)
            reply = FALLBACK_REPLY
            self._remember(state, text, reply)
            return reply
        except LLMProviderError:
            logger.exception("llm_provider_failed sender=%s", state.sender_id)
            reply = FALLBACK_REPLY
            self._remember(state, text, reply)
            return reply
        except Exception:
            logger.exception("llm_agent_failed sender=%s", state.sender_id)
            reply = FALLBACK_REPLY
            self._remember(state, text, reply)
            return reply

    def _run_tool(self, call: LLMToolCall, state: ConversationState) -> str:
        logger.info("tool_call sender=%s name=%s", state.sender_id, call.name)
        result = self.executor.execute(call.name, call.arguments, state)
        success = result.success
        error_code = result.error.error_code if result.error else None
        logger.info(
            "tool_result sender=%s name=%s success=%s error=%s",
            state.sender_id,
            call.name,
            success,
            error_code,
        )
        # Refresh caches after mutating tools.
        if call.name in {"create_vehicle", "create_booking", "cancel_booking", "reschedule_booking"}:
            self._refresh_context(state)
        return result.model_dump_json()

    def _refresh_context(self, state: ConversationState) -> None:
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

    def _build_messages(self, state: ConversationState, text: str) -> list[LLMMessage]:
        messages = [
            LLMMessage(role="system", content=build_whatsapp_system_prompt(today=date.today())),
            LLMMessage(role="system", content=self._session_context(state)),
        ]
        for item in state.message_history[-HISTORY_LIMIT:]:
            role = item.get("role")
            content = item.get("content")
            if role in {"user", "assistant"} and content:
                messages.append(LLMMessage(role=role, content=content))  # type: ignore[arg-type]
        messages.append(LLMMessage(role="user", content=text))
        return messages

    def _session_context(self, state: ConversationState) -> str:
        payload = {
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
            "SESSION CONTEXT (source of truth for IDs; do not invent missing IDs):\n"
            + json.dumps(payload, default=str)
        )

    @staticmethod
    def _remember(state: ConversationState, user_text: str, assistant_text: str) -> None:
        state.message_history.append({"role": "user", "content": user_text})
        state.message_history.append({"role": "assistant", "content": assistant_text})
        if len(state.message_history) > HISTORY_LIMIT * 2:
            state.message_history = state.message_history[-(HISTORY_LIMIT * 2) :]

    @staticmethod
    def _sanitize_customer_reply(reply: str) -> str:
        lowered = reply.lower()
        blocked_phrases = (
            "system prompt",
            "api key",
            "database",
            "ignore previous",
            "tool_call",
            "stack trace",
        )
        if any(phrase in lowered for phrase in blocked_phrases) and "booking" not in lowered:
            return (
                "I can help with car wash bookings, services, rescheduling, and cancellations. "
                "What would you like to do?"
            )
        return reply
