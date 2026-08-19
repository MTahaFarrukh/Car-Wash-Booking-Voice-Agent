"""WhatsApp conversation agent built on Phase 5 agent tools."""

from __future__ import annotations

import uuid
from datetime import date, time

from app.agent.service import AgentIntegrationService
from app.models.booking import BookingSource, BookingStatus
from app.schemas.agent import (
    AvailabilityToolInput,
    BookingCancelToolInput,
    BookingCreateToolInput,
    BookingRescheduleToolInput,
    CustomerLookupInput,
    ServicesListInput,
    VehicleCreateToolInput,
    VehicleLookupInput,
)
from app.services.booking_service import BookingService
from app.whatsapp.parser import (
    detect_intent,
    extract_entities,
    format_booking_summary,
    format_date,
    format_time,
    is_affirmation,
    is_greeting,
    is_negation,
    match_service,
    match_vehicle,
    normalize_text,
    parse_date,
    parse_time,
    uuid_from_string,
    vehicle_label,
)
from app.whatsapp.state import ConversationState


ACTIVE_BOOKING_STATUSES = {BookingStatus.PENDING, BookingStatus.CONFIRMED}


class WhatsAppConversationAgent:
    """Rule-based conversational layer that orchestrates Phase 5 tools."""

    def __init__(self, agent: AgentIntegrationService, booking_service: BookingService) -> None:
        self.agent = agent
        self.booking_service = booking_service

    def handle_message(self, state: ConversationState, text: str) -> str:
        if not text.strip():
            return "Please send me a text message with what you'd like to do."

        intent = detect_intent(text)
        self._refresh_catalog(state)
        self._apply_extracted_entities(state, text)

        if state.awaiting_confirmation:
            if is_affirmation(text) or intent == "confirm":
                return self._finalize_booking(state)
            if is_negation(text) or intent == "deny":
                state.awaiting_confirmation = False
                return "No problem — I won't place that booking. What would you like instead?"

        if intent == "greeting" or (is_greeting(text) and not self._has_booking_context(state)):
            return self._greeting(state)

        if intent == "list_services":
            return self._list_services(state)

        if intent == "cancel":
            return self._handle_cancel(state, text)

        if intent == "reschedule":
            return self._handle_reschedule(state, text)

        if intent == "book" or self._has_booking_context(state):
            return self._handle_booking_flow(state, text, explicit=intent == "book")

        if "vehicle" in normalize_text(text) and state.customer_id:
            return self._handle_vehicle_setup(state, text)

        return (
            "I can help you book a car wash, check services, reschedule, or cancel a booking. "
            "For example, say: \"I'd like a premium wash tomorrow at 3pm.\""
        )

    def _greeting(self, state: ConversationState) -> str:
        name = state.customer_name or "there"
        return (
            f"Hi {name}! Welcome to Sparkle Car Wash. "
            "I can help you book a wash, check available services, reschedule, or cancel a booking. "
            "What would you like to do today?"
        )

    def _refresh_catalog(self, state: ConversationState) -> None:
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

    def _apply_extracted_entities(self, state: ConversationState, text: str) -> None:
        entities = extract_entities(
            text,
            services=state.cached_services,
            vehicles=state.cached_vehicles,
        )
        if entities["service"]:
            service = entities["service"]
            state.selected_service_id = uuid_from_string(service["service_id"])
            state.selected_service_name = service["name"]
        if entities["vehicle"]:
            vehicle = entities["vehicle"]
            state.selected_vehicle_id = uuid_from_string(vehicle["vehicle_id"])
            state.selected_vehicle_label = vehicle_label(vehicle)
        if entities["date"]:
            state.requested_date = entities["date"]
        if entities["time"]:
            state.requested_time = entities["time"]

    def _has_booking_context(self, state: ConversationState) -> bool:
        return any(
            [
                state.selected_service_id,
                state.requested_date,
                state.requested_time,
                state.pending_intent == "book",
            ]
        )

    def _list_services(self, state: ConversationState) -> str:
        if not state.cached_services:
            return "Sorry, I couldn't load our services right now. Please try again shortly."
        lines = ["Here are our available services:"]
        for service in state.cached_services:
            price = service.get("price", "")
            duration = service.get("duration_minutes")
            lines.append(f"• {service['name']} — {duration} min, PKR {price}")
        lines.append("Tell me which service you'd like and when you'd prefer to come in.")
        return "\n".join(lines)

    def _handle_vehicle_setup(self, state: ConversationState, text: str) -> str:
        if not state.customer_id:
            return "Let's start with your booking request first."

        matched = match_vehicle(text, state.cached_vehicles)
        if matched:
            state.selected_vehicle_id = uuid_from_string(matched["vehicle_id"])
            state.selected_vehicle_label = vehicle_label(matched)
            return f"Got it — I'll use your {state.selected_vehicle_label}."

        normalized = normalize_text(text)
        if "add" in normalized or "new vehicle" in normalized or "register" in normalized:
            return (
                "Please share your vehicle details like: \"Toyota Corolla sedan\" "
                "or \"Honda Civic ABC-123\"."
            )
        return self._prompt_for_vehicle(state)

    def _prompt_for_vehicle(self, state: ConversationState) -> str:
        if not state.cached_vehicles:
            return (
                "I don't have a vehicle on file for you yet. "
                "Please tell me the make and model, for example: \"Honda Civic\"."
            )
        if len(state.cached_vehicles) == 1:
            vehicle = state.cached_vehicles[0]
            state.selected_vehicle_id = uuid_from_string(vehicle["vehicle_id"])
            state.selected_vehicle_label = vehicle_label(vehicle)
            return f"I'll use your {state.selected_vehicle_label}."
        options = ", ".join(vehicle_label(item) for item in state.cached_vehicles)
        return f"Which vehicle would you like to use? You have: {options}."

    def _resolve_vehicle(self, state: ConversationState, text: str) -> str | None:
        if state.selected_vehicle_id:
            return None
        if "my car" in normalize_text(text) or "my vehicle" in normalize_text(text):
            if len(state.cached_vehicles) == 1:
                vehicle = state.cached_vehicles[0]
                state.selected_vehicle_id = uuid_from_string(vehicle["vehicle_id"])
                state.selected_vehicle_label = vehicle_label(vehicle)
                return None
            if len(state.cached_vehicles) > 1:
                return self._prompt_for_vehicle(state)
        matched = match_vehicle(text, state.cached_vehicles)
        if matched:
            state.selected_vehicle_id = uuid_from_string(matched["vehicle_id"])
            state.selected_vehicle_label = vehicle_label(matched)
            return None
        if not state.cached_vehicles:
            created = self._create_vehicle_from_text(state, text)
            if created:
                return None
            return (
                "I don't have a vehicle on file for you yet. "
                "Please tell me the make and model, for example: \"Honda Civic\"."
            )
        return self._prompt_for_vehicle(state)

    def _create_vehicle_from_text(self, state: ConversationState, text: str) -> bool:
        if state.customer_id is None:
            return False
        stop_words = {
            "book", "booking", "schedule", "my", "for", "a", "the", "wash", "basic", "premium",
            "detailing", "full", "car", "tomorrow", "today", "at", "on", "need", "want",
        }
        tokens = [
            token
            for token in re_split_words(text)
            if token.lower() not in stop_words and len(token) >= 2
        ]
        if len(tokens) < 2:
            return False
        make, model = tokens[0].title(), tokens[1].title()
        vehicle_type = "sedan"
        lowered = normalize_text(text)
        for candidate in ("suv", "hatchback", "sedan", "truck"):
            if candidate in lowered:
                vehicle_type = candidate
                break
        result = self.agent.create_vehicle(
            VehicleCreateToolInput(
                customer_id=state.customer_id,
                vehicle_type=vehicle_type,
                make=make,
                model=model,
            )
        )
        if not result.success or not result.data:
            return False
        state.selected_vehicle_id = uuid_from_string(result.data["vehicle_id"])
        state.selected_vehicle_label = f"{make} {model}"
        state.cached_vehicles.append(result.data)
        return True

    def _handle_booking_flow(self, state: ConversationState, text: str, *, explicit: bool) -> str:
        state.pending_intent = "book"

        vehicle_prompt = self._resolve_vehicle(state, text)
        if vehicle_prompt:
            return vehicle_prompt

        if not state.selected_service_id:
            matched = match_service(text, state.cached_services)
            if matched:
                state.selected_service_id = uuid_from_string(matched["service_id"])
                state.selected_service_name = matched["name"]
            else:
                return (
                    "Which service would you like? "
                    "Say \"list services\" to see options, or mention Basic, Premium, or Full Detailing."
                )

        if not state.requested_date:
            parsed_date = parse_date(text)
            if parsed_date:
                state.requested_date = parsed_date
            else:
                return "What date would you like to come in? For example: tomorrow or Saturday."

        if not state.requested_time:
            parsed_time = parse_time(text)
            if parsed_time:
                state.requested_time = parsed_time
            else:
                return f"What time works for you on {format_date(state.requested_date)}?"

        availability = self.agent.check_availability(
            AvailabilityToolInput(
                booking_date=state.requested_date,
                service_id=state.selected_service_id,
                requested_time=state.requested_time,
            )
        )
        if not availability.success:
            return self._tool_error_message(availability.error.message if availability.error else "Availability check failed")

        if not availability.data.get("available"):
            alternatives = availability.data.get("available_slots", [])
            if alternatives:
                slots = ", ".join(format_time(time.fromisoformat(slot)) for slot in alternatives[:5])
                return (
                    f"Sorry, {format_time(state.requested_time)} isn't available on "
                    f"{format_date(state.requested_date)}. "
                    f"Here are some open times: {slots}. Which would you prefer?"
                )
            return (
                f"Sorry, {format_time(state.requested_time)} isn't available on "
                f"{format_date(state.requested_date)}. Please choose another date or time."
            )

        summary = format_booking_summary(
            service_name=state.selected_service_name or "car wash",
            booking_date=state.requested_date,
            booking_time=state.requested_time,
            vehicle_label=state.selected_vehicle_label,
        )

        if is_affirmation(text):
            return self._finalize_booking(state)

        if not state.awaiting_confirmation:
            state.awaiting_confirmation = True
            return f"{format_time(state.requested_time)} is available for {summary}. Would you like me to book it?"

        return f"Great — {summary}. Would you like me to book it?"

    def _finalize_booking(self, state: ConversationState) -> str:
        if not all([state.customer_id, state.selected_vehicle_id, state.selected_service_id, state.requested_date, state.requested_time]):
            state.awaiting_confirmation = False
            return "I'm still missing some booking details. Let's start with the service you'd like."

        result = self.agent.create_booking(
            BookingCreateToolInput(
                customer_id=state.customer_id,
                vehicle_id=state.selected_vehicle_id,
                service_id=state.selected_service_id,
                booking_date=state.requested_date,
                booking_time=state.requested_time,
                source=BookingSource.WHATSAPP,
            )
        )
        state.awaiting_confirmation = False
        state.pending_intent = None

        if not result.success:
            return self._tool_error_message(result.error.message if result.error else "Booking failed")

        summary = format_booking_summary(
            service_name=state.selected_service_name or "car wash",
            booking_date=state.requested_date,
            booking_time=state.requested_time,
            vehicle_label=state.selected_vehicle_label,
        )
        if result.data and result.data.get("duplicate"):
            return f"You already have a booking for {summary}."
        return f"You're all set! Your booking is confirmed for {summary}."

    def _handle_cancel(self, state: ConversationState, text: str) -> str:
        if not state.customer_id:
            return "I couldn't find your customer profile yet. Please say hi first so I can look you up."

        bookings = state.cached_active_bookings or self._load_active_bookings(state.customer_id)
        state.cached_active_bookings = bookings
        if not bookings:
            return "You don't have any active bookings to cancel."

        if len(bookings) == 1:
            booking_id = uuid_from_string(bookings[0]["booking_id"])
        else:
            matched = self._match_booking_from_text(text, bookings)
            if matched:
                booking_id = uuid_from_string(matched["booking_id"])
            elif state.target_booking_id:
                booking_id = state.target_booking_id
            else:
                state.pending_intent = "cancel"
                options = "; ".join(
                    f"{item['service_name']} on {item['booking_date']} at {item['booking_time']}"
                    for item in bookings
                )
                return f"Which booking would you like to cancel? Active bookings: {options}."

        result = self.agent.cancel_booking(BookingCancelToolInput(booking_id=booking_id))
        state.pending_intent = None
        state.target_booking_id = None
        if not result.success:
            return self._tool_error_message(result.error.message if result.error else "Cancellation failed")
        return "Your booking has been cancelled. Let me know if you'd like to book another time."

    def _handle_reschedule(self, state: ConversationState, text: str) -> str:
        if not state.customer_id:
            return "I couldn't find your customer profile yet. Please say hi first so I can look you up."

        bookings = state.cached_active_bookings or self._load_active_bookings(state.customer_id)
        state.cached_active_bookings = bookings
        if not bookings:
            return "You don't have any active bookings to reschedule."

        booking = None
        if len(bookings) == 1:
            booking = bookings[0]
        else:
            booking = self._match_booking_from_text(text, bookings)
            if booking is None:
                state.pending_intent = "reschedule"
                options = "; ".join(
                    f"{item['service_name']} on {item['booking_date']} at {item['booking_time']}"
                    for item in bookings
                )
                return f"Which booking should I move? Active bookings: {options}."

        new_date = parse_date(text) or state.requested_date
        new_time = parse_time(text) or state.requested_time
        if new_date:
            state.requested_date = new_date
        if new_time:
            state.requested_time = new_time

        if not state.requested_date:
            state.target_booking_id = uuid_from_string(booking["booking_id"])
            return "What date would you like to move it to?"
        if not state.requested_time:
            state.target_booking_id = uuid_from_string(booking["booking_id"])
            return f"What time would you prefer on {format_date(state.requested_date)}?"

        service_id = uuid_from_string(booking["service_id"])
        availability = self.agent.check_availability(
            AvailabilityToolInput(
                booking_date=state.requested_date,
                service_id=service_id,
                requested_time=state.requested_time,
            )
        )
        if not availability.success:
            return self._tool_error_message(availability.error.message if availability.error else "Availability check failed")
        if not availability.data.get("available"):
            alternatives = availability.data.get("available_slots", [])
            if alternatives:
                slots = ", ".join(format_time(time.fromisoformat(slot)) for slot in alternatives[:5])
                return f"That time isn't available. Open times include: {slots}."
            return "That time isn't available. Please choose another date or time."

        result = self.agent.reschedule_booking(
            BookingRescheduleToolInput(
                booking_id=uuid_from_string(booking["booking_id"]),
                booking_date=state.requested_date,
                booking_time=state.requested_time,
            )
        )
        state.pending_intent = None
        state.target_booking_id = None
        if not result.success:
            return self._tool_error_message(result.error.message if result.error else "Reschedule failed")

        return (
            f"Done! Your {booking['service_name']} booking is now scheduled for "
            f"{format_date(state.requested_date)} at {format_time(state.requested_time)}."
        )

    def _match_booking_from_text(self, text: str, bookings: list[dict]) -> dict | None:
        normalized = normalize_text(text)
        for booking in bookings:
            if booking["service_name"].lower() in normalized:
                return booking
            if booking["booking_date"] in normalized:
                return booking
        return None

    @staticmethod
    def _tool_error_message(message: str) -> str:
        return f"Sorry, something went wrong: {message}. Please try again or adjust your request."


def re_split_words(text: str) -> list[str]:
    import re

    return re.findall(r"[A-Za-z0-9-]+", text)
