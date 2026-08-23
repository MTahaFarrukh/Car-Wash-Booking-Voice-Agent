"""Tests for Phase 6 WhatsApp conversational booking agent."""

from __future__ import annotations

import uuid
from datetime import date, time, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.agent.service import AgentIntegrationService
from app.main import app
from app.models.customer import Customer
from app.models.service import Service
from app.models.vehicle import Vehicle
from app.schemas.agent import AgentError, AgentResult, CustomerToolInput, VehicleCreateToolInput
from app.services.availability_service import AvailabilityService
from app.whatsapp.parser import match_service, parse_date, parse_time
from app.whatsapp.state import conversation_state_store
from tests.conftest import requires_database

client = TestClient(app)
BRIDGE_HEADERS = {"X-WhatsApp-Bridge-Secret": "test-bridge-secret"}


def _future_weekday(days_ahead: int = 14) -> date:
    candidate = date.today() + timedelta(days=days_ahead)
    while candidate.weekday() > 4:
        candidate += timedelta(days=1)
    return candidate


def _pick_available_slot(db_session, service_id) -> tuple[date, time]:
    availability = AvailabilityService(db_session)
    for days_ahead in range(14, 90):
        booking_date = _future_weekday(days_ahead)
        slots = availability.get_available_slots(booking_date, service_id)
        if slots:
            return booking_date, slots[0]
    raise AssertionError("No available slot found")


def _phone_suffix(width: int = 8) -> str:
    """Numeric-only suffix so generated phones stay E.164 digit-valid."""
    modulo = 10**width
    return f"{uuid.uuid4().int % modulo:0{width}d}"


def _whatsapp_payload(**overrides) -> dict:
    suffix = _phone_suffix()
    payload = {
        "message_id": f"msg-{suffix}",
        "sender_id": f"92300{suffix}@s.whatsapp.net",
        "phone_number": f"+92300{suffix}",
        "text": "Hi",
        "timestamp": "2026-08-20T10:00:00Z",
        "message_type": "text",
    }
    payload.update(overrides)
    return payload


@pytest.fixture(autouse=True)
def reset_conversation_state():
    conversation_state_store._states.clear()
    yield
    conversation_state_store._states.clear()


class TestWhatsAppParser:
    def test_parse_date_tomorrow(self):
        today = date(2026, 8, 20)
        assert parse_date("Book tomorrow at 3pm", today=today) == date(2026, 8, 21)

    def test_parse_time_pm(self):
        assert parse_time("Book at 3pm") == time(15, 0)

    def test_match_service_premium(self):
        services = [{"service_id": "1", "name": "Premium Wash"}]
        matched = match_service("I want a premium wash", services)
        assert matched is not None
        assert matched["name"] == "Premium Wash"


@requires_database
class TestWhatsAppAgent:
    def test_incoming_greeting(self, db_session):
        payload = _whatsapp_payload(text="Hi")
        response = client.post("/api/whatsapp/messages", json=payload, headers=BRIDGE_HEADERS)
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert "Sparkle Car Wash" in body["message"]
        assert body["recipient"] == payload["sender_id"]

    def test_invalid_payload_rejected(self):
        response = client.post("/api/whatsapp/messages", json={"text": "Hi"}, headers=BRIDGE_HEADERS)
        assert response.status_code == 422

    def test_invalid_bridge_secret_rejected(self):
        payload = _whatsapp_payload()
        response = client.post(
            "/api/whatsapp/messages",
            json=payload,
            headers={"X-WhatsApp-Bridge-Secret": "wrong-secret"},
        )
        assert response.status_code == 401

    def test_existing_customer_identification(self, db_session):
        customer = db_session.scalar(select(Customer).limit(1))
        payload = _whatsapp_payload(phone_number=customer.phone, sender_id="923001111111@s.whatsapp.net", text="Hi")
        response = client.post("/api/whatsapp/messages", json=payload, headers=BRIDGE_HEADERS)
        assert response.status_code == 200
        assert customer.name.split()[0] in response.json()["message"] or "Hi" in response.json()["message"]

    def test_new_customer_creation(self, db_session):
        suffix = _phone_suffix()
        phone = f"+92331{suffix}"
        payload = _whatsapp_payload(
            phone_number=phone,
            sender_id=f"92331{suffix}@s.whatsapp.net",
            text="Hello",
        )
        response = client.post("/api/whatsapp/messages", json=payload, headers=BRIDGE_HEADERS)
        assert response.status_code == 200
        created = db_session.scalar(select(Customer).where(Customer.phone == phone))
        assert created is not None

    def test_service_listing(self, db_session):
        payload = _whatsapp_payload(text="What services do you have?")
        response = client.post("/api/whatsapp/messages", json=payload, headers=BRIDGE_HEADERS)
        assert response.status_code == 200
        message = response.json()["message"]
        assert "Basic Wash" in message or "Premium Wash" in message

    def test_existing_vehicle_auto_selection(self, db_session):
        customer = db_session.scalar(select(Customer).limit(1))
        vehicles = db_session.scalars(select(Vehicle).where(Vehicle.customer_id == customer.id)).all()
        assert len(vehicles) >= 1
        service = db_session.scalar(select(Service).where(Service.name == "Premium Wash"))
        booking_date, slot = _pick_available_slot(db_session, service.id)
        vehicle = vehicles[0]

        payload = _whatsapp_payload(
            phone_number=customer.phone,
            sender_id=f"92300{_phone_suffix(6)}@s.whatsapp.net",
            text=(
                f"Book my {vehicle.make} {vehicle.model} for premium wash "
                f"on {booking_date.isoformat()} at {slot.strftime('%H:%M')}. Yes"
            ),
        )
        response = client.post("/api/whatsapp/messages", json=payload, headers=BRIDGE_HEADERS)
        assert response.status_code == 200
        assert "confirmed" in response.json()["message"].lower() or "set" in response.json()["message"].lower()

    def test_multiple_vehicle_ambiguity(self, db_session):
        suffix = _phone_suffix()
        phone = f"+92332{suffix}"
        sender = f"92332{suffix}@s.whatsapp.net"

        agent = AgentIntegrationService(db_session)
        created = agent.find_or_create_customer(
            CustomerToolInput(
                name=f"Multi Vehicle {suffix}",
                phone=phone,
            )
        )
        customer_id = uuid.UUID(created.data["customer_id"])
        agent.create_vehicle(
            VehicleCreateToolInput(
                customer_id=customer_id,
                vehicle_type="sedan",
                make="Honda",
                model="Civic",
            )
        )
        agent.create_vehicle(
            VehicleCreateToolInput(
                customer_id=customer_id,
                vehicle_type="suv",
                make="Toyota",
                model="Fortuner",
            )
        )

        payload = _whatsapp_payload(phone_number=phone, sender_id=sender, text="Book my car for basic wash tomorrow at 10am")
        response = client.post("/api/whatsapp/messages", json=payload, headers=BRIDGE_HEADERS)
        assert response.status_code == 200
        assert "which vehicle" in response.json()["message"].lower()

    def test_unavailable_requested_time(self, db_session):
        customer = db_session.scalar(select(Customer).limit(1))
        service = db_session.scalar(select(Service).where(Service.name == "Basic Wash"))
        booking_date, slot = _pick_available_slot(db_session, service.id)
        vehicle = db_session.scalar(select(Vehicle).where(Vehicle.customer_id == customer.id).limit(1))

        first = _whatsapp_payload(
            phone_number=customer.phone,
            sender_id=f"92333{_phone_suffix(6)}@s.whatsapp.net",
            text=(
                f"Book my {vehicle.make} {vehicle.model} for basic wash "
                f"on {booking_date.isoformat()} at {slot.strftime('%H:%M')}. Yes"
            ),
        )
        assert client.post("/api/whatsapp/messages", json=first, headers=BRIDGE_HEADERS).status_code == 200

        second = _whatsapp_payload(
            phone_number=f"+92334{_phone_suffix(6)}",
            sender_id=f"92334{_phone_suffix(6)}@s.whatsapp.net",
            text=(
                f"Book my Honda Civic for basic wash on {booking_date.isoformat()} "
                f"at {slot.strftime('%H:%M')}. Yes"
            ),
        )
        response = client.post("/api/whatsapp/messages", json=second, headers=BRIDGE_HEADERS)
        assert response.status_code == 200
        message = response.json()["message"].lower()
        assert "isn't available" in message or "open times" in message or "sorry" in message

    def test_successful_booking_with_confirmation(self, db_session):
        suffix = _phone_suffix()
        phone = f"+92335{suffix}"
        sender = f"92335{suffix}@s.whatsapp.net"
        service = db_session.scalar(select(Service).where(Service.name == "Basic Wash"))
        booking_date, slot = _pick_available_slot(db_session, service.id)

        hi = client.post(
            "/api/whatsapp/messages",
            json=_whatsapp_payload(phone_number=phone, sender_id=sender, text="Hi"),
            headers=BRIDGE_HEADERS,
        )
        assert hi.status_code == 200

        request = client.post(
            "/api/whatsapp/messages",
            json=_whatsapp_payload(
                message_id=f"msg-req-{suffix}",
                phone_number=phone,
                sender_id=sender,
                text=f"Book Honda Civic for basic wash on {booking_date.isoformat()} at {slot.strftime('%H:%M')}",
            ),
            headers=BRIDGE_HEADERS,
        )
        assert request.status_code == 200
        assert "book it" in request.json()["message"].lower()

        confirm = client.post(
            "/api/whatsapp/messages",
            json=_whatsapp_payload(
                message_id=f"msg-yes-{suffix}",
                phone_number=phone,
                sender_id=sender,
                text="Yes",
            ),
            headers=BRIDGE_HEADERS,
        )
        assert confirm.status_code == 200
        assert "confirmed" in confirm.json()["message"].lower()

    def test_cancellation_single_active_booking(self, db_session):
        suffix = _phone_suffix()
        phone = f"+92336{suffix}"
        sender = f"92336{suffix}@s.whatsapp.net"
        service = db_session.scalar(select(Service).where(Service.name == "Basic Wash"))
        booking_date, slot = _pick_available_slot(db_session, service.id)

        client.post(
            "/api/whatsapp/messages",
            json=_whatsapp_payload(phone_number=phone, sender_id=sender, text="Hi"),
            headers=BRIDGE_HEADERS,
        )
        client.post(
            "/api/whatsapp/messages",
            json=_whatsapp_payload(
                message_id=f"book-{suffix}",
                phone_number=phone,
                sender_id=sender,
                text=f"Book Honda Civic basic wash {booking_date.isoformat()} {slot.strftime('%H:%M')}. Yes",
            ),
            headers=BRIDGE_HEADERS,
        )
        cancel = client.post(
            "/api/whatsapp/messages",
            json=_whatsapp_payload(
                message_id=f"cancel-{suffix}",
                phone_number=phone,
                sender_id=sender,
                text="Cancel my booking",
            ),
            headers=BRIDGE_HEADERS,
        )
        assert cancel.status_code == 200
        assert "cancelled" in cancel.json()["message"].lower()

    def test_reschedule_booking(self, db_session):
        suffix = _phone_suffix()
        phone = f"+92337{suffix}"
        sender = f"92337{suffix}@s.whatsapp.net"
        service = db_session.scalar(select(Service).where(Service.name == "Basic Wash"))
        booking_date, slots = _pick_available_slot(db_session, service.id)
        availability = AvailabilityService(db_session)
        alternatives = [
            slot
            for slot in availability.get_available_slots(booking_date, service.id)
            if slot != slots
        ]
        assert alternatives, "Need at least two slots"
        new_slot = alternatives[0]

        client.post(
            "/api/whatsapp/messages",
            json=_whatsapp_payload(phone_number=phone, sender_id=sender, text="Hi"),
            headers=BRIDGE_HEADERS,
        )
        client.post(
            "/api/whatsapp/messages",
            json=_whatsapp_payload(
                message_id=f"book-{suffix}",
                phone_number=phone,
                sender_id=sender,
                text=f"Book Honda Civic basic wash {booking_date.isoformat()} {slots.strftime('%H:%M')}. Yes",
            ),
            headers=BRIDGE_HEADERS,
        )
        move = client.post(
            "/api/whatsapp/messages",
            json=_whatsapp_payload(
                message_id=f"move-{suffix}",
                phone_number=phone,
                sender_id=sender,
                text=f"Move my booking to {booking_date.isoformat()} at {new_slot.strftime('%H:%M')}",
            ),
            headers=BRIDGE_HEADERS,
        )
        assert move.status_code == 200
        assert "scheduled" in move.json()["message"].lower() or "done" in move.json()["message"].lower()

    def test_missing_information_prompt(self, db_session):
        payload = _whatsapp_payload(text="I want to book a wash")
        response = client.post("/api/whatsapp/messages", json=payload, headers=BRIDGE_HEADERS)
        assert response.status_code == 200
        message = response.json()["message"].lower()
        assert "service" in message or "date" in message or "vehicle" in message

    def test_duplicate_message_id_returns_same_response(self, db_session):
        payload = _whatsapp_payload(text="Hi")
        first = client.post("/api/whatsapp/messages", json=payload, headers=BRIDGE_HEADERS)
        second = client.post("/api/whatsapp/messages", json=payload, headers=BRIDGE_HEADERS)
        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["message"] == second.json()["message"]

    def test_unsupported_message_type(self, db_session):
        payload = _whatsapp_payload(text="", message_type="image")
        response = client.post("/api/whatsapp/messages", json=payload, headers=BRIDGE_HEADERS)
        assert response.status_code == 200
        assert "text messages" in response.json()["message"].lower()

    def test_agent_tool_failure_returns_safe_message(self, db_session):
        suffix = _phone_suffix()
        phone = f"+92338{suffix}"
        sender = f"92338{suffix}@s.whatsapp.net"
        service = db_session.scalar(select(Service).where(Service.name == "Basic Wash"))
        booking_date, slot = _pick_available_slot(db_session, service.id)

        client.post(
            "/api/whatsapp/messages",
            json=_whatsapp_payload(phone_number=phone, sender_id=sender, text="Hi"),
            headers=BRIDGE_HEADERS,
        )
        client.post(
            "/api/whatsapp/messages",
            json=_whatsapp_payload(
                message_id=f"setup-{suffix}",
                phone_number=phone,
                sender_id=sender,
                text=f"Book Honda Civic for basic wash on {booking_date.isoformat()} at {slot.strftime('%H:%M')}",
            ),
            headers=BRIDGE_HEADERS,
        )

        failing_payload = _whatsapp_payload(
            message_id=f"fail-{_phone_suffix()}",
            phone_number=phone,
            sender_id=sender,
            text="Yes",
        )
        with patch(
            "app.whatsapp.conversation.WhatsAppConversationAgent._finalize_booking",
            return_value="Sorry, something went wrong: simulated failure. Please try again or adjust your request.",
        ):
            response = client.post("/api/whatsapp/messages", json=failing_payload, headers=BRIDGE_HEADERS)
        assert response.status_code == 200
        assert "sorry" in response.json()["message"].lower()

    def test_backend_safe_error_from_tool(self, db_session):
        payload = _whatsapp_payload(text="Hi")
        client.post("/api/whatsapp/messages", json=payload, headers=BRIDGE_HEADERS)

        with patch(
            "app.agent.service.AgentIntegrationService.list_services",
            return_value=AgentResult(
                success=False,
                data=None,
                error=AgentError(error_code="UNKNOWN_ERROR", message="simulated outage"),
            ),
        ):
            response = client.post(
                "/api/whatsapp/messages",
                json=_whatsapp_payload(message_id=f"svc-{_phone_suffix(6)}", text="What services do you have?"),
                headers=BRIDGE_HEADERS,
            )
        assert response.status_code == 200
        assert "sorry" in response.json()["message"].lower() or "couldn't load" in response.json()["message"].lower()
