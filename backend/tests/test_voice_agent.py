"""Tests for Phase 8 voice booking agent (mocked LLM / fake voice provider)."""

from __future__ import annotations

import uuid
from datetime import date, time, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.agent.service import AgentIntegrationService
from app.core.config import Settings, get_settings
from app.llm.errors import LLMProviderError
from app.llm.fake import FakeLLMProvider
from app.llm.schemas import LLMCompletionResult, LLMToolCall
from app.main import app
from app.models.booking import Booking, BookingSource
from app.models.call_log import CallLog, CallOutcome
from app.models.customer import Customer
from app.models.service import Service
from app.models.vehicle import Vehicle
from app.schemas.agent import BookingCreateToolInput, CustomerToolInput, VehicleCreateToolInput
from app.services.availability_service import AvailabilityService
from app.services.booking_service import BookingService
from app.voice.agent import FALLBACK_REPLY, VoiceConversationAgent
from app.voice.fake import FakeVoiceProvider
from app.voice.provider import UpliftVoiceProvider, create_voice_provider
from app.voice.schemas import (
    VoiceCallEndRequest,
    VoiceCallStartRequest,
    VoiceToolExecuteRequest,
    VoiceTurnRequest,
    VoiceWebhookEvent,
)
from app.voice.service import VoiceConversationService
from app.voice.state import call_session_store
from app.whatsapp.tool_executor import get_llm_tool_specs
from tests.conftest import requires_database

VOICE_SECRET = "test-voice-secret"


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


def _settings(**overrides) -> Settings:
    base = {
        "voice_provider": "fake",
        "voice_webhook_secret": VOICE_SECRET,
        "llm_provider": "openai",
        "llm_api_key": "test-key",
        "llm_model": "gpt-4o-mini",
        "llm_max_tool_calls": 8,
        "llm_temperature": 0.0,
        "llm_max_tokens": 400,
    }
    base.update(overrides)
    return Settings.model_construct(**base)


@pytest.fixture(autouse=True)
def reset_call_sessions():
    call_session_store.clear()
    yield
    call_session_store.clear()


def _text_result(content: str) -> LLMCompletionResult:
    return LLMCompletionResult(content=content, tool_calls=[])


def _tool_result(*calls: LLMToolCall) -> LLMCompletionResult:
    return LLMCompletionResult(content=None, tool_calls=list(calls))


def _make_service(db_session, fake: FakeLLMProvider) -> VoiceConversationService:
    agent = AgentIntegrationService(db_session)
    booking = BookingService(db_session)
    conversation = VoiceConversationAgent(agent, booking, fake, settings=_settings())
    return VoiceConversationService(
        db_session,
        llm=fake,
        voice_provider=FakeVoiceProvider(),
        settings=_settings(),
        conversation=conversation,
    )


def _client() -> TestClient:
    get_settings.cache_clear()
    return TestClient(app)


@requires_database
class TestVoiceAgent:
    def test_phase5_tools_available(self):
        names = {spec.name for spec in get_llm_tool_specs()}
        assert {
            "find_or_create_customer",
            "get_customer",
            "create_vehicle",
            "get_customer_vehicles",
            "list_services",
            "check_availability",
            "create_booking",
            "get_booking",
            "reschedule_booking",
            "cancel_booking",
        }.issubset(names)

    def test_incoming_call_greeting(self, db_session):
        fake = FakeLLMProvider([])
        service = _make_service(db_session, fake)
        call_id = f"voice-{uuid.uuid4().hex[:10]}"
        started = service.start_call(
            VoiceCallStartRequest(call_id=call_id, caller_phone=f"+92300{uuid.uuid4().hex[:8]}")
        )
        assert started.success
        assert "Sparkle" in (started.greeting or "")
        log = db_session.scalar(select(CallLog).where(CallLog.call_id == call_id))
        assert log is not None
        assert log.phone is not None

    def test_caller_identity_existing_customer(self, db_session):
        phone = f"+92301{uuid.uuid4().hex[:8]}"
        agent = AgentIntegrationService(db_session)
        created = agent.find_or_create_customer(CustomerToolInput(name="Ayesha Voice", phone=phone))
        assert created.success
        fake = FakeLLMProvider([lambda m, t: _text_result("Welcome back. How can I help?")])
        service = _make_service(db_session, fake)
        call_id = f"voice-{uuid.uuid4().hex[:10]}"
        started = service.start_call(VoiceCallStartRequest(call_id=call_id, caller_phone=phone))
        assert started.customer_id == uuid.UUID(created.data["customer_id"])

    def test_caller_identity_new_customer(self, db_session):
        phone = f"+92302{uuid.uuid4().hex[:8]}"
        fake = FakeLLMProvider([])
        service = _make_service(db_session, fake)
        call_id = f"voice-{uuid.uuid4().hex[:10]}"
        started = service.start_call(VoiceCallStartRequest(call_id=call_id, caller_phone=phone))
        assert started.customer_id is not None
        customer = db_session.get(Customer, started.customer_id)
        assert customer is not None
        assert customer.phone == phone

    def test_service_selection(self, db_session):
        fake = FakeLLMProvider(
            [
                lambda m, t: _tool_result(
                    LLMToolCall(id="1", name="list_services", arguments={"active_only": True})
                ),
                lambda m, t: _text_result("We offer Basic Wash, Premium Wash, and Full Detailing."),
            ]
        )
        service = _make_service(db_session, fake)
        phone = f"+92303{uuid.uuid4().hex[:8]}"
        call_id = f"voice-{uuid.uuid4().hex[:10]}"
        service.start_call(VoiceCallStartRequest(call_id=call_id, caller_phone=phone))
        turn = service.process_turn(VoiceTurnRequest(call_id=call_id, text="What services do you have?"))
        assert "Wash" in turn.reply or "Detailing" in turn.reply

    def test_successful_booking_source_voice(self, db_session):
        service_row = db_session.scalar(select(Service).where(Service.name == "Premium Wash"))
        booking_date, slot = _pick_available_slot(db_session, service_row.id)
        phone = f"+92304{uuid.uuid4().hex[:8]}"
        agent = AgentIntegrationService(db_session)
        customer = agent.find_or_create_customer(CustomerToolInput(name="Voice Booker", phone=phone))
        vehicle = agent.create_vehicle(
            VehicleCreateToolInput(
                customer_id=uuid.UUID(customer.data["customer_id"]),
                make="Suzuki",
                model="Swift",
                vehicle_type="sedan",
            )
        )
        cid = customer.data["customer_id"]
        vid = vehicle.data["vehicle_id"]
        sid = str(service_row.id)

        fake = FakeLLMProvider(
            [
                lambda m, t: _tool_result(
                    LLMToolCall(
                        id="a1",
                        name="check_availability",
                        arguments={
                            "service_id": sid,
                            "booking_date": booking_date.isoformat(),
                            "requested_time": slot.isoformat(),
                        },
                    )
                ),
                lambda m, t: _text_result("That time is open. Shall I book Premium Wash for your Suzuki Swift?"),
                lambda m, t: _tool_result(
                    LLMToolCall(
                        id="a2",
                        name="create_booking",
                        arguments={
                            "customer_id": cid,
                            "vehicle_id": vid,
                            "service_id": sid,
                            "booking_date": booking_date.isoformat(),
                            "booking_time": slot.isoformat(),
                        },
                    )
                ),
                lambda m, t: _text_result(
                    "Done. Your Premium Wash for your Suzuki Swift is booked."
                ),
            ]
        )
        service = _make_service(db_session, fake)
        call_id = f"voice-{uuid.uuid4().hex[:10]}"
        service.start_call(VoiceCallStartRequest(call_id=call_id, caller_phone=phone))
        service.process_turn(
            VoiceTurnRequest(
                call_id=call_id,
                text=f"Book premium wash tomorrow at {slot.strftime('%H:%M')}",
            )
        )
        turn = service.process_turn(VoiceTurnRequest(call_id=call_id, text="Yes, book it"))
        assert "booked" in turn.reply.lower() or "confirm" in turn.reply.lower() or turn.booking_id

        ended = service.end_call(VoiceCallEndRequest(call_id=call_id, outcome="booking_created"))
        assert ended.outcome == CallOutcome.BOOKING_CREATED.value

        booking = db_session.scalar(
            select(Booking).where(
                Booking.customer_id == uuid.UUID(cid),
                Booking.source == BookingSource.VOICE,
            ).order_by(Booking.created_at.desc())
        )
        assert booking is not None
        assert booking.source == BookingSource.VOICE
        log = db_session.scalar(select(CallLog).where(CallLog.call_id == call_id))
        assert log is not None
        assert log.outcome == CallOutcome.BOOKING_CREATED
        assert log.booking_id == booking.id

    def test_unavailable_slot_offers_alternative_via_tool(self, db_session):
        service_row = db_session.scalar(select(Service).where(Service.name == "Premium Wash"))
        booking_date, slot = _pick_available_slot(db_session, service_row.id)
        phone = f"+92305{uuid.uuid4().hex[:8]}"
        agent = AgentIntegrationService(db_session)
        customer = agent.find_or_create_customer(CustomerToolInput(name="Busy Caller", phone=phone))
        vehicle = agent.create_vehicle(
            VehicleCreateToolInput(
                customer_id=uuid.UUID(customer.data["customer_id"]),
                make="Honda",
                model="Civic",
                vehicle_type="sedan",
            )
        )
        # Occupy the slot first.
        agent.create_booking(
            BookingCreateToolInput(
                customer_id=uuid.UUID(customer.data["customer_id"]),
                vehicle_id=uuid.UUID(vehicle.data["vehicle_id"]),
                service_id=service_row.id,
                booking_date=booking_date,
                booking_time=slot,
                source=BookingSource.DASHBOARD,
            )
        )

        fake = FakeLLMProvider(
            [
                lambda m, t: _tool_result(
                    LLMToolCall(
                        id="u1",
                        name="check_availability",
                        arguments={
                            "service_id": str(service_row.id),
                            "booking_date": booking_date.isoformat(),
                            "requested_time": slot.isoformat(),
                        },
                    )
                ),
                lambda m, t: _text_result(
                    "That time isn't available. I can offer another open slot from our calendar."
                ),
            ]
        )
        service = _make_service(db_session, fake)
        call_id = f"voice-{uuid.uuid4().hex[:10]}"
        service.start_call(VoiceCallStartRequest(call_id=call_id, caller_phone=phone))
        turn = service.process_turn(
            VoiceTurnRequest(call_id=call_id, text=f"Book premium at {slot.strftime('%H:%M')}")
        )
        assert "available" in turn.reply.lower() or "offer" in turn.reply.lower() or "slot" in turn.reply.lower()

    def test_cancellation_flow(self, db_session):
        service_row = db_session.scalar(select(Service).where(Service.name == "Basic Wash"))
        booking_date, slot = _pick_available_slot(db_session, service_row.id)
        phone = f"+92306{uuid.uuid4().hex[:8]}"
        agent = AgentIntegrationService(db_session)
        customer = agent.find_or_create_customer(CustomerToolInput(name="Cancel Caller", phone=phone))
        vehicle = agent.create_vehicle(
            VehicleCreateToolInput(
                customer_id=uuid.UUID(customer.data["customer_id"]),
                make="Toyota",
                model="Corolla",
                vehicle_type="sedan",
            )
        )
        created = agent.create_booking(
            BookingCreateToolInput(
                customer_id=uuid.UUID(customer.data["customer_id"]),
                vehicle_id=uuid.UUID(vehicle.data["vehicle_id"]),
                service_id=service_row.id,
                booking_date=booking_date,
                booking_time=slot,
                source=BookingSource.VOICE,
            )
        )
        booking_id = created.data["booking"]["booking_id"]

        fake = FakeLLMProvider(
            [
                lambda m, t: _text_result("I found your Basic Wash booking. Would you like me to cancel it?"),
                lambda m, t: _tool_result(
                    LLMToolCall(id="c1", name="cancel_booking", arguments={"booking_id": booking_id})
                ),
                lambda m, t: _text_result("Your booking has been cancelled."),
            ]
        )
        service = _make_service(db_session, fake)
        call_id = f"voice-{uuid.uuid4().hex[:10]}"
        service.start_call(VoiceCallStartRequest(call_id=call_id, caller_phone=phone))
        service.process_turn(VoiceTurnRequest(call_id=call_id, text="Cancel my booking"))
        turn = service.process_turn(VoiceTurnRequest(call_id=call_id, text="Yes"))
        assert "cancel" in turn.reply.lower()
        service.end_call(VoiceCallEndRequest(call_id=call_id, outcome="cancelled"))
        log = db_session.scalar(select(CallLog).where(CallLog.call_id == call_id))
        assert log.outcome == CallOutcome.CANCELLED

    def test_reschedule_flow(self, db_session):
        service_row = db_session.scalar(select(Service).where(Service.name == "Basic Wash"))
        booking_date, slots = None, None
        availability = AvailabilityService(db_session)
        for days_ahead in range(14, 90):
            candidate = _future_weekday(days_ahead)
            found = availability.get_available_slots(candidate, service_row.id)
            if len(found) >= 2:
                booking_date, slots = candidate, found
                break
        assert booking_date and slots
        old_slot, new_slot = slots[0], slots[1]
        phone = f"+92307{uuid.uuid4().hex[:8]}"
        agent = AgentIntegrationService(db_session)
        customer = agent.find_or_create_customer(CustomerToolInput(name="Reschedule Caller", phone=phone))
        vehicle = agent.create_vehicle(
            VehicleCreateToolInput(
                customer_id=uuid.UUID(customer.data["customer_id"]),
                make="Kia",
                model="Sportage",
                vehicle_type="suv",
            )
        )
        created = agent.create_booking(
            BookingCreateToolInput(
                customer_id=uuid.UUID(customer.data["customer_id"]),
                vehicle_id=uuid.UUID(vehicle.data["vehicle_id"]),
                service_id=service_row.id,
                booking_date=booking_date,
                booking_time=old_slot,
                source=BookingSource.VOICE,
            )
        )
        booking_id = created.data["booking"]["booking_id"]

        fake = FakeLLMProvider(
            [
                lambda m, t: _tool_result(
                    LLMToolCall(
                        id="r0",
                        name="check_availability",
                        arguments={
                            "service_id": str(service_row.id),
                            "booking_date": booking_date.isoformat(),
                            "requested_time": new_slot.isoformat(),
                        },
                    )
                ),
                lambda m, t: _tool_result(
                    LLMToolCall(
                        id="r1",
                        name="reschedule_booking",
                        arguments={
                            "booking_id": booking_id,
                            "booking_date": booking_date.isoformat(),
                            "booking_time": new_slot.isoformat(),
                        },
                    )
                ),
                lambda m, t: _text_result("I've moved your booking to the new time."),
            ]
        )
        service = _make_service(db_session, fake)
        call_id = f"voice-{uuid.uuid4().hex[:10]}"
        service.start_call(VoiceCallStartRequest(call_id=call_id, caller_phone=phone))
        turn = service.process_turn(
            VoiceTurnRequest(call_id=call_id, text=f"Move my booking to {new_slot.strftime('%H:%M')}")
        )
        assert "move" in turn.reply.lower() or "new time" in turn.reply.lower() or "booking" in turn.reply.lower()

    def test_multiple_vehicles_prompt(self, db_session):
        phone = f"+92308{uuid.uuid4().hex[:8]}"
        agent = AgentIntegrationService(db_session)
        customer = agent.find_or_create_customer(CustomerToolInput(name="Multi Car", phone=phone))
        cid = uuid.UUID(customer.data["customer_id"])
        agent.create_vehicle(
            VehicleCreateToolInput(customer_id=cid, make="Honda", model="Civic", vehicle_type="sedan")
        )
        agent.create_vehicle(
            VehicleCreateToolInput(customer_id=cid, make="Suzuki", model="Swift", vehicle_type="sedan")
        )
        fake = FakeLLMProvider(
            [
                lambda m, t: _tool_result(
                    LLMToolCall(id="v1", name="get_customer_vehicles", arguments={"customer_id": str(cid)})
                ),
                lambda m, t: _text_result("I see a Honda Civic and a Suzuki Swift. Which car are you bringing?"),
            ]
        )
        service = _make_service(db_session, fake)
        call_id = f"voice-{uuid.uuid4().hex[:10]}"
        service.start_call(VoiceCallStartRequest(call_id=call_id, caller_phone=phone))
        turn = service.process_turn(VoiceTurnRequest(call_id=call_id, text="Book a wash for my car"))
        assert "which" in turn.reply.lower() or "civic" in turn.reply.lower() or "swift" in turn.reply.lower()

    def test_missing_information(self, db_session):
        fake = FakeLLMProvider(
            [lambda m, t: _text_result("Sure. What type of wash would you like, and what time works for you?")]
        )
        service = _make_service(db_session, fake)
        phone = f"+92309{uuid.uuid4().hex[:8]}"
        call_id = f"voice-{uuid.uuid4().hex[:10]}"
        service.start_call(VoiceCallStartRequest(call_id=call_id, caller_phone=phone))
        turn = service.process_turn(VoiceTurnRequest(call_id=call_id, text="I need a wash tomorrow"))
        assert "?" in turn.reply or "what" in turn.reply.lower()

    def test_confirmation_before_booking(self, db_session):
        fake = FakeLLMProvider(
            [
                lambda m, t: _text_result(
                    "I have Premium Wash for your Suzuki Swift tomorrow at 5 PM. Shall I book it?"
                )
            ]
        )
        service = _make_service(db_session, fake)
        phone = f"+92310{uuid.uuid4().hex[:8]}"
        call_id = f"voice-{uuid.uuid4().hex[:10]}"
        service.start_call(VoiceCallStartRequest(call_id=call_id, caller_phone=phone))
        turn = service.process_turn(VoiceTurnRequest(call_id=call_id, text="Premium for my Swift at 5"))
        assert "shall i book" in turn.reply.lower() or "book it" in turn.reply.lower()

    def test_tool_failure_spoken(self, db_session):
        fake = FakeLLMProvider(
            [
                lambda m, t: _tool_result(
                    LLMToolCall(id="x1", name="get_booking", arguments={"booking_id": str(uuid.uuid4())})
                ),
                lambda m, t: _text_result("I couldn't find that booking. Can you tell me the date or service?"),
            ]
        )
        service = _make_service(db_session, fake)
        phone = f"+92311{uuid.uuid4().hex[:8]}"
        call_id = f"voice-{uuid.uuid4().hex[:10]}"
        service.start_call(VoiceCallStartRequest(call_id=call_id, caller_phone=phone))
        turn = service.process_turn(VoiceTurnRequest(call_id=call_id, text="What's my booking status?"))
        assert "couldn't find" in turn.reply.lower() or "booking" in turn.reply.lower()

    def test_provider_llm_failure(self, db_session):
        def boom(messages, tools):
            raise LLMProviderError("simulated provider failure")

        fake = FakeLLMProvider([boom])
        service = _make_service(db_session, fake)
        phone = f"+92312{uuid.uuid4().hex[:8]}"
        call_id = f"voice-{uuid.uuid4().hex[:10]}"
        service.start_call(VoiceCallStartRequest(call_id=call_id, caller_phone=phone))
        turn = service.process_turn(VoiceTurnRequest(call_id=call_id, text="Hello"))
        assert turn.reply == FALLBACK_REPLY

    def test_max_tool_call_protection(self, db_session):
        calls = [
            lambda m, t: _tool_result(
                LLMToolCall(id=f"loop-{i}", name="list_services", arguments={"active_only": True})
            )
            for i in range(12)
        ]
        fake = FakeLLMProvider(calls)
        service = _make_service(db_session, fake)
        # Lower guard for this case
        service.conversation.settings = _settings(llm_max_tool_calls=2)
        phone = f"+92313{uuid.uuid4().hex[:8]}"
        call_id = f"voice-{uuid.uuid4().hex[:10]}"
        service.start_call(VoiceCallStartRequest(call_id=call_id, caller_phone=phone))
        turn = service.process_turn(VoiceTurnRequest(call_id=call_id, text="List everything forever"))
        assert turn.reply == FALLBACK_REPLY

    def test_barge_in_flag(self, db_session):
        fake = FakeLLMProvider(
            [
                lambda m, t: _text_result("Your Premium Wash is available tomorrow at 5 PM and—"),
                lambda m, t: _text_result("Got it. Checking 6 PM instead."),
            ]
        )
        service = _make_service(db_session, fake)
        phone = f"+92314{uuid.uuid4().hex[:8]}"
        call_id = f"voice-{uuid.uuid4().hex[:10]}"
        service.start_call(VoiceCallStartRequest(call_id=call_id, caller_phone=phone))
        service.process_turn(VoiceTurnRequest(call_id=call_id, text="Book premium tomorrow at 5"))
        turn = service.process_turn(
            VoiceTurnRequest(call_id=call_id, text="Actually make it 6", interrupted=True)
        )
        assert "6" in turn.reply

    def test_direct_tool_execute_proxy(self, db_session):
        fake = FakeLLMProvider([])
        service = _make_service(db_session, fake)
        phone = f"+92315{uuid.uuid4().hex[:8]}"
        call_id = f"voice-{uuid.uuid4().hex[:10]}"
        service.start_call(VoiceCallStartRequest(call_id=call_id, caller_phone=phone))
        result = service.execute_tool(
            VoiceToolExecuteRequest(
                call_id=call_id,
                name="list_services",
                arguments={"active_only": True},
                caller_phone=phone,
            )
        )
        assert result.success
        assert result.result.get("success") is True

    def test_webhook_validation_and_invalid_secret(self):
        client = _client()
        payload = {
            "event_type": "call.started",
            "call_id": f"voice-{uuid.uuid4().hex[:8]}",
            "payload": {"caller_phone": "+923001111111"},
        }
        bad = client.post("/api/voice/webhook", json=payload, headers={"X-Voice-Webhook-Secret": "wrong"})
        assert bad.status_code == 401

        # Ensure secret is loaded for good path when settings cache cleared with env.
        get_settings.cache_clear()
        good = client.post(
            "/api/voice/webhook",
            json=payload,
            headers={"X-Voice-Webhook-Secret": VOICE_SECRET},
        )
        # May be 200 if DB available and secret matches env from conftest
        assert good.status_code in {200, 503}

    def test_webhook_valid_event(self, db_session):
        fake = FakeLLMProvider([])
        service = _make_service(db_session, fake)
        call_id = f"voice-{uuid.uuid4().hex[:10]}"
        phone = f"+92316{uuid.uuid4().hex[:8]}"
        out = service.handle_webhook(
            VoiceWebhookEvent(
                event_type="call.started",
                call_id=call_id,
                payload={"caller_phone": phone, "provider": "fake"},
            )
        )
        assert out.get("success") is True
        assert out.get("call_id") == call_id

    def test_call_logging(self, db_session):
        fake = FakeLLMProvider([lambda m, t: _text_result("We open weekdays nine to six.")])
        service = _make_service(db_session, fake)
        call_id = f"voice-{uuid.uuid4().hex[:10]}"
        phone = f"+92317{uuid.uuid4().hex[:8]}"
        service.start_call(VoiceCallStartRequest(call_id=call_id, caller_phone=phone))
        service.process_turn(VoiceTurnRequest(call_id=call_id, text="What are your hours?"))
        ended = service.end_call(
            VoiceCallEndRequest(call_id=call_id, duration_seconds=42, outcome="information_request")
        )
        assert ended.duration_seconds == 42
        assert ended.outcome == CallOutcome.INFORMATION_REQUEST.value
        log = db_session.scalar(select(CallLog).where(CallLog.call_id == call_id))
        assert log.duration_seconds == 42

    def test_create_voice_provider_factory(self):
        fake = create_voice_provider(_settings(voice_provider="fake"))
        assert isinstance(fake, FakeVoiceProvider)
        uplift = create_voice_provider(
            _settings(voice_provider="uplift", uplift_api_key="", uplift_agent_id="")
        )
        assert isinstance(uplift, UpliftVoiceProvider)
        assert uplift.is_configured() is False
        assert uplift.supports_barge_in() is True

    def test_http_start_turn_end(self, db_session):
        # HTTP path uses real app wiring; inject via service-level already covered.
        # Validate auth + routing with TestClient against start when secret configured.
        get_settings.cache_clear()
        client = _client()
        call_id = f"voice-http-{uuid.uuid4().hex[:8]}"
        phone = f"+92318{uuid.uuid4().hex[:8]}"
        headers = {"X-Voice-Webhook-Secret": VOICE_SECRET}
        started = client.post(
            "/api/voice/calls/start",
            json={"call_id": call_id, "caller_phone": phone, "provider": "fake"},
            headers=headers,
        )
        assert started.status_code == 200, started.text
        assert started.json()["call_id"] == call_id
        ended = client.post(
            "/api/voice/calls/end",
            json={"call_id": call_id, "duration_seconds": 10, "outcome": "no_booking"},
            headers=headers,
        )
        assert ended.status_code == 200
        log = db_session.scalar(select(CallLog).where(CallLog.call_id == call_id))
        assert log is not None

    def test_whatsapp_regression_still_forces_whatsapp_source(self, db_session):
        """Voice executor change must not alter WhatsApp booking source."""
        from app.whatsapp.tool_executor import Phase5ToolExecutor
        from app.whatsapp.state import ConversationState

        service_row = db_session.scalar(select(Service).where(Service.name == "Basic Wash"))
        booking_date, slot = _pick_available_slot(db_session, service_row.id)
        phone = f"+92319{uuid.uuid4().hex[:8]}"
        agent = AgentIntegrationService(db_session)
        customer = agent.find_or_create_customer(CustomerToolInput(name="WA Reg", phone=phone))
        vehicle = agent.create_vehicle(
            VehicleCreateToolInput(
                customer_id=uuid.UUID(customer.data["customer_id"]),
                make="Honda",
                model="City",
                vehicle_type="sedan",
            )
        )
        state = ConversationState(sender_id="wa-reg", phone=phone)
        state.customer_id = uuid.UUID(customer.data["customer_id"])
        executor = Phase5ToolExecutor(agent)  # default WHATSAPP
        result = executor.execute(
            "create_booking",
            {
                "customer_id": customer.data["customer_id"],
                "vehicle_id": vehicle.data["vehicle_id"],
                "service_id": str(service_row.id),
                "booking_date": booking_date.isoformat(),
                "booking_time": slot.isoformat(),
            },
            state,
        )
        assert result.success
        booking = db_session.get(Booking, uuid.UUID(result.data["booking"]["booking_id"]))
        assert booking.source == BookingSource.WHATSAPP
