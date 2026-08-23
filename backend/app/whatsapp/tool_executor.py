"""Expose Phase 5 tools to LLM providers in a controlled registry."""

from __future__ import annotations

import logging
from datetime import date, time
from typing import Any, Callable

from pydantic import ValidationError

from app.agent.service import AgentIntegrationService
from app.llm.schemas import LLMToolSpec
from app.models.booking import BookingSource
from app.schemas.agent import (
    AgentError,
    AgentResult,
    AvailabilityToolInput,
    BookingCancelToolInput,
    BookingCreateToolInput,
    BookingLookupInput,
    BookingRescheduleToolInput,
    CustomerLookupInput,
    CustomerToolInput,
    ServicesListInput,
    VehicleCreateToolInput,
    VehicleLookupInput,
)
from app.whatsapp.parser import uuid_from_string, vehicle_label
from app.whatsapp.state import ConversationState

logger = logging.getLogger(__name__)

# LLM-oriented descriptions (Phase 5 handlers remain unchanged).
TOOL_DESCRIPTIONS: dict[str, str] = {
    "find_or_create_customer": (
        "Find or create the customer profile. Call this after the customer gives their real name "
        "and/or mobile number. Use the session phone when available."
    ),
    "get_customer": "Look up an existing customer by customer_id or phone before booking operations.",
    "create_vehicle": (
        "Register a vehicle for the current customer. Use only after confirming make/model "
        "(and optional type/registration)."
    ),
    "get_customer_vehicles": (
        "List vehicles saved for the customer. Call this before booking if vehicle choice is unclear."
    ),
    "list_services": (
        "List real car-wash services with duration and price. Never invent services; always use this tool."
    ),
    "check_availability": (
        "Check whether a service has available booking slots on a specific date and optionally at a "
        "requested time. Never assume availability. Use ISO date (YYYY-MM-DD) and HH:MM:SS time."
    ),
    "create_booking": (
        "Create a booking only after customer, vehicle, service, date, and time are known AND "
        "check_availability confirmed the slot. Never claim success unless this tool succeeds."
    ),
    "get_booking": "Fetch a booking by booking_id for confirmation, updates, or cancellation.",
    "reschedule_booking": (
        "Move an existing booking to a new date/time after verifying availability. "
        "Use booking_id from session context or a prior tool result."
    ),
    "cancel_booking": (
        "Cancel an existing booking by booking_id. If multiple active bookings exist, ask which one first."
    ),
}

INPUT_MODELS = {
    "find_or_create_customer": CustomerToolInput,
    "get_customer": CustomerLookupInput,
    "create_vehicle": VehicleCreateToolInput,
    "get_customer_vehicles": VehicleLookupInput,
    "list_services": ServicesListInput,
    "check_availability": AvailabilityToolInput,
    "create_booking": BookingCreateToolInput,
    "get_booking": BookingLookupInput,
    "reschedule_booking": BookingRescheduleToolInput,
    "cancel_booking": BookingCancelToolInput,
}


def _openai_parameters(model_cls: type) -> dict[str, Any]:
    schema = model_cls.model_json_schema()
    # Prefer a flat object schema for tool calling.
    schema.pop("title", None)
    return schema


def get_llm_tool_specs() -> list[LLMToolSpec]:
    """Return Phase 5 tools in provider-agnostic tool-calling format."""
    specs: list[LLMToolSpec] = []
    for name, model_cls in INPUT_MODELS.items():
        specs.append(
            LLMToolSpec(
                name=name,
                description=TOOL_DESCRIPTIONS[name],
                parameters=_openai_parameters(model_cls),
            )
        )
    return specs


class Phase5ToolExecutor:
    """Dispatch LLM tool calls to AgentIntegrationService only."""

    def __init__(
        self,
        agent: AgentIntegrationService,
        *,
        booking_source: BookingSource = BookingSource.WHATSAPP,
    ) -> None:
        self.agent = agent
        self.booking_source = booking_source
        self._handlers: dict[str, Callable[[Any], AgentResult]] = {
            "find_or_create_customer": self.agent.find_or_create_customer,
            "get_customer": self.agent.get_customer,
            "create_vehicle": self.agent.create_vehicle,
            "get_customer_vehicles": self.agent.get_customer_vehicles,
            "list_services": self.agent.list_services,
            "check_availability": self.agent.check_availability,
            "create_booking": self.agent.create_booking,
            "get_booking": self.agent.get_booking,
            "reschedule_booking": self.agent.reschedule_booking,
            "cancel_booking": self.agent.cancel_booking,
        }

    def execute(self, name: str, arguments: dict[str, Any], state: ConversationState) -> AgentResult:
        if name not in self._handlers:
            return AgentResult(
                success=False,
                data=None,
                error=AgentError(
                    error_code="VALIDATION_ERROR",
                    message=f"Unknown tool: {name}",
                    retryable=False,
                    suggested_action="Use only the provided booking tools",
                ),
            )

        cleaned = self._prepare_arguments(name, dict(arguments or {}), state)
        if name == "create_booking":
            blocked = self._booking_identity_block(state)
            if blocked is not None:
                return blocked
        model_cls = INPUT_MODELS[name]
        try:
            payload = model_cls.model_validate(cleaned)
        except ValidationError:
            logger.info("tool_validation_failed name=%s", name)
            return AgentResult(
                success=False,
                data=None,
                error=AgentError(
                    error_code="VALIDATION_ERROR",
                    message="Invalid tool arguments",
                    retryable=False,
                    suggested_action="Ask the customer for missing details",
                ),
            )

        result = self._handlers[name](payload)
        self._update_state_from_result(name, result, state)
        return result

    @staticmethod
    def _booking_identity_block(state: ConversationState) -> AgentResult | None:
        from app.whatsapp.service import WhatsAppService

        if state.needs_phone or not state.phone:
            return AgentResult(
                success=False,
                data=None,
                error=AgentError(
                    error_code="VALIDATION_ERROR",
                    message="Customer mobile number is required before booking",
                    retryable=True,
                    suggested_action="Ask for their mobile number with country code, then call find_or_create_customer",
                ),
            )
        if state.needs_name or WhatsAppService.is_placeholder_name(state.customer_name):
            return AgentResult(
                success=False,
                data=None,
                error=AgentError(
                    error_code="VALIDATION_ERROR",
                    message="Customer name is required before booking",
                    retryable=True,
                    suggested_action="Ask for their full name, then call find_or_create_customer",
                ),
            )
        return None

    def _prepare_arguments(self, name: str, arguments: dict[str, Any], state: ConversationState) -> dict[str, Any]:
        # Never trust the model to switch customers mid-session.
        if name in {"create_vehicle", "get_customer_vehicles", "create_booking"} and state.customer_id:
            arguments["customer_id"] = str(state.customer_id)
        if name == "get_customer" and state.customer_id and not arguments.get("customer_id") and not arguments.get("phone"):
            arguments["customer_id"] = str(state.customer_id)
        if name == "find_or_create_customer" and state.phone and not arguments.get("phone"):
            arguments["phone"] = state.phone
        if name == "create_booking":
            arguments["source"] = self.booking_source.value
            if state.selected_vehicle_id and not arguments.get("vehicle_id"):
                arguments["vehicle_id"] = str(state.selected_vehicle_id)
            if state.selected_service_id and not arguments.get("service_id"):
                arguments["service_id"] = str(state.selected_service_id)
            if state.requested_date and not arguments.get("booking_date"):
                arguments["booking_date"] = state.requested_date.isoformat()
            if state.requested_time and not arguments.get("booking_time"):
                arguments["booking_time"] = state.requested_time.isoformat()
        if name == "check_availability":
            if state.selected_service_id and not arguments.get("service_id"):
                arguments["service_id"] = str(state.selected_service_id)
            if state.requested_date and not arguments.get("booking_date"):
                arguments["booking_date"] = state.requested_date.isoformat()
            if state.requested_time and not arguments.get("requested_time"):
                arguments["requested_time"] = state.requested_time.isoformat()
        if name in {"reschedule_booking", "cancel_booking", "get_booking"}:
            if state.target_booking_id and not arguments.get("booking_id"):
                arguments["booking_id"] = str(state.target_booking_id)
        return arguments

    def _update_state_from_result(self, name: str, result: AgentResult, state: ConversationState) -> None:
        if not result.success or not result.data:
            return
        data = result.data
        try:
            if name in {"find_or_create_customer", "get_customer"}:
                if data.get("customer_id"):
                    state.customer_id = uuid_from_string(data["customer_id"])
                state.customer_name = data.get("name") or state.customer_name
                state.phone = data.get("phone") or state.phone
                from app.whatsapp.service import WhatsAppService

                state.needs_name = WhatsAppService.is_placeholder_name(state.customer_name)
                state.needs_phone = not bool(state.phone)
            elif name == "list_services":
                state.cached_services = data.get("services") or []
            elif name == "get_customer_vehicles":
                state.cached_vehicles = data.get("vehicles") or []
            elif name == "create_vehicle":
                state.selected_vehicle_id = uuid_from_string(data["vehicle_id"])
                state.selected_vehicle_label = vehicle_label(data)
                state.cached_vehicles.append(data)
            elif name == "check_availability":
                if data.get("requested_date"):
                    state.requested_date = date.fromisoformat(data["requested_date"])
                if data.get("requested_time"):
                    state.requested_time = time.fromisoformat(data["requested_time"])
                service = data.get("service") or {}
                if service.get("service_id"):
                    state.selected_service_id = uuid_from_string(service["service_id"])
                    state.selected_service_name = service.get("name") or state.selected_service_name
            elif name == "create_booking":
                booking = data.get("booking") or {}
                if booking.get("booking_id"):
                    state.target_booking_id = uuid_from_string(booking["booking_id"])
                if booking.get("booking_date"):
                    state.requested_date = date.fromisoformat(str(booking["booking_date"]))
                if booking.get("booking_time"):
                    state.requested_time = time.fromisoformat(str(booking["booking_time"]))
                state.awaiting_confirmation = False
                state.pending_intent = None
            elif name == "reschedule_booking":
                booking = data.get("booking") or {}
                if booking.get("booking_id"):
                    state.target_booking_id = uuid_from_string(booking["booking_id"])
                if booking.get("booking_date"):
                    state.requested_date = date.fromisoformat(str(booking["booking_date"]))
                if booking.get("booking_time"):
                    state.requested_time = time.fromisoformat(str(booking["booking_time"]))
                state.pending_intent = None
            elif name == "cancel_booking":
                state.target_booking_id = None
                state.pending_intent = None
                state.cached_active_bookings = [
                    item
                    for item in state.cached_active_bookings
                    if item.get("booking_id") != data.get("booking_id")
                ]
        except (TypeError, ValueError, KeyError) as exc:
            logger.info("state_update_skipped name=%s error=%s", name, type(exc).__name__)
