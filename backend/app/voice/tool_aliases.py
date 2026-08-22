"""Map provider-friendly tool names/args onto Phase 5 tools (voice channel only)."""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime, time
from typing import Any

from app.agent.service import AgentIntegrationService
from app.models.booking import BookingSource
from app.schemas.agent import (
    AvailabilityToolInput,
    BookingCreateToolInput,
    CustomerToolInput,
    ServicesListInput,
    VehicleCreateToolInput,
    VehicleLookupInput,
)
from app.voice.state import CallSessionState
from app.whatsapp.parser import uuid_from_string

# VAPI / loose assistant tool names → Phase 5 (or composite voice helpers).
TOOL_ALIASES: dict[str, str] = {
    "save_booking": "save_booking",
    "savebooking": "save_booking",
    "book_appointment": "save_booking",
    "createbooking": "create_booking",
    "create_booking": "create_booking",
    "checkavailability": "check_availability",
    "listservices": "list_services",
    "cancelbooking": "cancel_booking",
    "reschedulebooking": "reschedule_booking",
}


def normalize_tool_name(name: str) -> str:
    key = re.sub(r"[\s\-]+", "_", (name or "").strip().lower())
    key = re.sub(r"[^a-z0-9_]", "", key)
    return TOOL_ALIASES.get(key, key)


def _pick(args: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in args and args[key] not in (None, ""):
            return args[key]
        # case-insensitive
        for existing, value in args.items():
            if str(existing).lower() == key.lower() and value not in (None, ""):
                return value
    return None


def _normalize_phone(raw: Any) -> str | None:
    if raw is None:
        return None
    digits = re.sub(r"\D", "", str(raw))
    if len(digits) < 7:
        return None
    if str(raw).strip().startswith("+"):
        return "+" + digits
    return "+" + digits


def _parse_date(raw: Any) -> date | None:
    if raw is None:
        return None
    if isinstance(raw, date) and not isinstance(raw, datetime):
        return raw
    text = str(raw).strip()
    for fmt in ("%Y-%m-%d", "%d %B %Y", "%d %b %Y", "%B %d %Y", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _parse_time(raw: Any) -> time | None:
    if raw is None:
        return None
    if isinstance(raw, time):
        return raw
    text = str(raw).strip().upper().replace(".", "")
    for fmt in ("%H:%M:%S", "%H:%M", "%I:%M %p", "%I %p", "%I:%M%p", "%I%p"):
        try:
            return datetime.strptime(text, fmt).time().replace(second=0, microsecond=0)
        except ValueError:
            continue
    return None


def _parse_vehicle(args: dict[str, Any]) -> tuple[str, str, str]:
    make = str(_pick(args, "make", "vehicle_make") or "").strip()
    model = str(_pick(args, "model", "vehicle_model") or "").strip()
    vtype = str(_pick(args, "vehicle_type", "type", "vehicleType") or "sedan").strip() or "sedan"
    label = str(_pick(args, "vehicle", "vehicle_name", "car", "vehicle_label") or "").strip()
    if (not make or not model) and label:
        parts = label.split()
        if len(parts) >= 2:
            make = make or parts[0]
            model = model or " ".join(parts[1:])
        elif parts:
            make = make or parts[0]
            model = model or parts[0]
    if not make:
        make = "Unknown"
    if not model:
        model = "Car"
    return make, model, vtype


def execute_save_booking(
    agent: AgentIntegrationService,
    state: CallSessionState,
    arguments: dict[str, Any],
) -> tuple[dict[str, Any], str | None]:
    """
    Composite helper for VAPI-style save_booking tools.

    Still uses only Phase 5 AgentIntegrationService methods — no SQL.
    """
    args = dict(arguments or {})
    phone = _normalize_phone(_pick(args, "phone", "phone_number", "customer_phone", "caller_phone")) or state.phone
    name = str(_pick(args, "name", "customer_name", "caller_name") or state.customer_name or "Voice Caller").strip()
    booking_date = _parse_date(_pick(args, "booking_date", "preferred_date", "date"))
    booking_time = _parse_time(_pick(args, "booking_time", "preferred_time", "time"))
    service_hint = str(_pick(args, "service", "service_name", "wash_type") or "Premium Wash").strip()

    if not phone:
        return (
            {
                "success": False,
                "error": {
                    "error_code": "VALIDATION_ERROR",
                    "message": "Phone number is required",
                },
            },
            "I still need a phone number to save the booking.",
        )
    if not booking_date or not booking_time:
        return (
            {
                "success": False,
                "error": {
                    "error_code": "INVALID_BOOKING_TIME",
                    "message": "Date and time are required",
                },
            },
            "I need a clear date and time before I can book that.",
        )

    customer = agent.find_or_create_customer(CustomerToolInput(name=name, phone=phone))
    if not customer.success or not customer.data:
        return customer.model_dump(), "I couldn't save the customer details."
    customer_id = uuid_from_string(customer.data["customer_id"])
    state.customer_id = customer_id
    state.customer_name = customer.data.get("name") or name
    state.phone = phone

    make, model, vtype = _parse_vehicle(args)
    vehicles = agent.get_customer_vehicles(VehicleLookupInput(customer_id=customer_id))
    vehicle_id: uuid.UUID | None = None
    if vehicles.success and vehicles.data:
        for item in vehicles.data.get("vehicles") or []:
            label = f"{item.get('make', '')} {item.get('model', '')}".strip().lower()
            if make.lower() in label and model.lower().split()[0] in label:
                vehicle_id = uuid_from_string(item["vehicle_id"])
                break
    if vehicle_id is None:
        created = agent.create_vehicle(
            VehicleCreateToolInput(
                customer_id=customer_id,
                make=make,
                model=model,
                vehicle_type=vtype,
            )
        )
        if not created.success or not created.data:
            return created.model_dump(), "I couldn't save the vehicle details."
        vehicle_id = uuid_from_string(created.data["vehicle_id"])
    state.selected_vehicle_id = vehicle_id
    state.selected_vehicle_label = f"{make} {model}"

    services = agent.list_services(ServicesListInput(active_only=True))
    if not services.success or not services.data or not services.data.get("services"):
        return (
            {
                "success": False,
                "error": {"error_code": "SERVICE_NOT_FOUND", "message": "No services available"},
            },
            "I couldn't load our wash services right now.",
        )
    service_rows = services.data["services"]
    service_id = None
    service_name = None
    hint_l = service_hint.lower()
    for row in service_rows:
        row_name = str(row.get("name") or "")
        if hint_l in row_name.lower() or row_name.lower() in hint_l:
            service_id = uuid_from_string(row["service_id"])
            service_name = row_name
            break
    if service_id is None:
        # Prefer Premium Wash when unspecified
        for row in service_rows:
            if "premium" in str(row.get("name") or "").lower():
                service_id = uuid_from_string(row["service_id"])
                service_name = row.get("name")
                break
    if service_id is None:
        service_id = uuid_from_string(service_rows[0]["service_id"])
        service_name = service_rows[0].get("name")
    state.selected_service_id = service_id
    state.selected_service_name = service_name

    availability = agent.check_availability(
        AvailabilityToolInput(
            service_id=service_id,
            booking_date=booking_date,
            requested_time=booking_time,
        )
    )
    if not availability.success:
        return availability.model_dump(), (
            "That time isn't available. I can offer another open slot if you'd like."
        )
    avail_data = availability.data or {}
    if avail_data.get("available") is False:
        alts = avail_data.get("alternative_slots") or avail_data.get("available_slots") or []
        spoken = "That time isn't available."
        if alts:
            spoken += " I can suggest other open times from our calendar."
        return availability.model_dump(), spoken

    created_booking = agent.create_booking(
        BookingCreateToolInput(
            customer_id=customer_id,
            vehicle_id=vehicle_id,
            service_id=service_id,
            booking_date=booking_date,
            booking_time=booking_time,
            source=BookingSource.VOICE,
            notes=str(_pick(args, "notes") or "Booked via voice"),
        )
    )
    if created_booking.success and created_booking.data:
        booking = created_booking.data.get("booking") or {}
        if booking.get("booking_id"):
            state.last_booking_id = uuid_from_string(booking["booking_id"])
            state.target_booking_id = state.last_booking_id
        state.outcome_hint = "booking_created"
        state.requested_date = booking_date
        state.requested_time = booking_time
        spoken = (
            f"Done. Your {service_name or 'wash'} for your {make} {model} "
            f"is booked for {booking_date.isoformat()} at {booking_time.strftime('%H:%M')}."
        )
        return created_booking.model_dump(), spoken
    return created_booking.model_dump(), "I couldn't complete the booking just now."
