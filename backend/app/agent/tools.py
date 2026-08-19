"""Provider-independent tool definitions for conversational agents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.schemas.agent import (
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


@dataclass(frozen=True)
class AgentToolDefinition:
    """Metadata used to expose tools in any provider's function-calling format."""

    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    handler: str


def get_tool_definitions() -> list[AgentToolDefinition]:
    """Return canonical tool definitions for all agent operations."""
    output_schema = AgentResult.model_json_schema()
    return [
        AgentToolDefinition(
            name="find_or_create_customer",
            description="Use when you have customer identity details and need a reusable customer record.",
            input_schema=CustomerToolInput.model_json_schema(),
            output_schema=output_schema,
            handler="find_or_create_customer",
        ),
        AgentToolDefinition(
            name="get_customer",
            description="Use to fetch an existing customer by id or phone before booking operations.",
            input_schema=CustomerLookupInput.model_json_schema(),
            output_schema=output_schema,
            handler="get_customer",
        ),
        AgentToolDefinition(
            name="create_vehicle",
            description="Use after confirming customer identity to register a vehicle for bookings.",
            input_schema=VehicleCreateToolInput.model_json_schema(),
            output_schema=output_schema,
            handler="create_vehicle",
        ),
        AgentToolDefinition(
            name="get_customer_vehicles",
            description="Use to retrieve vehicles for a customer before creating or rescheduling bookings.",
            input_schema=VehicleLookupInput.model_json_schema(),
            output_schema=output_schema,
            handler="get_customer_vehicles",
        ),
        AgentToolDefinition(
            name="list_services",
            description="Use when the user asks for available wash/detailing services and durations.",
            input_schema=ServicesListInput.model_json_schema(),
            output_schema=output_schema,
            handler="list_services",
        ),
        AgentToolDefinition(
            name="check_availability",
            description="Use before booking to verify slot availability and suggest alternatives.",
            input_schema=AvailabilityToolInput.model_json_schema(),
            output_schema=output_schema,
            handler="check_availability",
        ),
        AgentToolDefinition(
            name="create_booking",
            description="Use to create a booking only after customer, vehicle, and service are validated.",
            input_schema=BookingCreateToolInput.model_json_schema(),
            output_schema=output_schema,
            handler="create_booking",
        ),
        AgentToolDefinition(
            name="get_booking",
            description="Use to fetch booking details for confirmation, updates, or cancellation.",
            input_schema=BookingLookupInput.model_json_schema(),
            output_schema=output_schema,
            handler="get_booking",
        ),
        AgentToolDefinition(
            name="reschedule_booking",
            description="Use to move an existing booking to a new date/time with availability validation.",
            input_schema=BookingRescheduleToolInput.model_json_schema(),
            output_schema=output_schema,
            handler="reschedule_booking",
        ),
        AgentToolDefinition(
            name="cancel_booking",
            description="Use to cancel an existing booking while preserving booking history.",
            input_schema=BookingCancelToolInput.model_json_schema(),
            output_schema=output_schema,
            handler="cancel_booking",
        ),
    ]
