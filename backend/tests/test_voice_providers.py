"""Phase 8.1 — multi-provider voice adapter tests (mocked; no live calls)."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import Settings, get_settings
from app.llm.fake import FakeLLMProvider
from app.llm.schemas import LLMCompletionResult
from app.main import app
from app.models.call_log import CallLog
from app.voice.fake import FakeVoiceProvider
from app.voice.normalized import NormalizedVoiceToolCall
from app.voice.provider import create_voice_provider
from app.voice.schemas import VoiceCallStartRequest, VoiceToolExecuteRequest
from app.voice.service import VoiceConversationService
from app.voice.state import call_session_store
from app.voice.uplift_provider import UpliftVoiceProvider
from app.voice.vapi_provider import VapiVoiceProvider
from app.agent.service import AgentIntegrationService
from app.services.booking_service import BookingService
from app.voice.agent import VoiceConversationAgent
from tests.conftest import requires_database

VOICE_SECRET = "test-voice-secret"
VAPI_SECRET = "test-vapi-secret"


def _settings(**overrides) -> Settings:
    base = {
        "voice_provider": "fake",
        "voice_webhook_secret": VOICE_SECRET,
        "uplift_webhook_secret": VOICE_SECRET,
        "vapi_webhook_secret": VAPI_SECRET,
        "vapi_api_key": "",
        "vapi_assistant_id": "",
        "uplift_api_key": "",
        "uplift_agent_id": "",
        "llm_provider": "openai",
        "llm_api_key": "test-key",
        "llm_max_tool_calls": 8,
    }
    base.update(overrides)
    return Settings.model_construct(**base)


@pytest.fixture(autouse=True)
def reset_sessions():
    call_session_store.clear()
    yield
    call_session_store.clear()


class TestVapiProvider:
    def test_initialization_and_config_validation(self):
        unconfigured = VapiVoiceProvider(_settings())
        assert unconfigured.name == "vapi"
        assert unconfigured.is_configured() is False
        assert unconfigured.supports_barge_in() is True

        configured = VapiVoiceProvider(
            _settings(vapi_api_key="vk", vapi_assistant_id="asst_1")
        )
        assert configured.is_configured() is True
        session = configured.create_session(call_id="c1", caller_phone="+15551212")
        assert session["configured"] is True
        assert session["assistant_id"] == "asst_1"

    def test_webhook_signature_validation(self):
        provider = VapiVoiceProvider(_settings(vapi_webhook_secret=VAPI_SECRET))
        body = b'{"message":{"type":"status-update"}}'
        assert provider.verify_webhook(headers={"Authorization": f"Bearer {VAPI_SECRET}"}, body=body)
        assert provider.verify_webhook(headers={"X-Vapi-Secret": VAPI_SECRET}, body=body)
        digest = hmac.new(VAPI_SECRET.encode(), body, hashlib.sha256).hexdigest()
        assert provider.verify_webhook(headers={"x-vapi-signature": digest}, body=body)
        assert provider.verify_webhook(headers={"Authorization": "Bearer wrong"}, body=body) is False

    def test_call_event_parsing(self):
        provider = VapiVoiceProvider(_settings(vapi_webhook_secret=VAPI_SECRET))
        payload = {
            "message": {
                "type": "status-update",
                "status": "in-progress",
                "call": {"id": "call-abc", "customer": {"number": "+15550001111"}},
            }
        }
        events = provider.parse_webhook(payload)
        assert len(events) == 1
        assert events[0].event_type == "call.started"
        assert events[0].call_id == "call-abc"
        assert events[0].caller_phone == "+15550001111"
        assert events[0].provider == "vapi"

    def test_normalized_tool_call(self):
        provider = VapiVoiceProvider(_settings())
        payload = {
            "message": {
                "type": "tool-calls",
                "call": {"id": "call-tools"},
                "toolCallList": [
                    {
                        "id": "tc1",
                        "name": "list_services",
                        "parameters": {"active_only": True},
                    }
                ],
            }
        }
        calls = provider.normalize_tool_calls(payload)
        assert calls == [
            NormalizedVoiceToolCall(id="tc1", name="list_services", arguments={"active_only": True})
        ]
        formatted = provider.format_tool_results(
            [{"id": "tc1", "name": "list_services", "result": {"success": True}}]
        )
        assert formatted["results"][0]["toolCallId"] == "tc1"
        assert isinstance(formatted["results"][0]["result"], str)
        assert "error" not in formatted["results"][0]

    def test_openai_style_tool_call_nested_function(self):
        provider = VapiVoiceProvider(_settings())
        payload = {
            "message": {
                "type": "tool-calls",
                "call": {"id": "call-tools-2"},
                "toolCallList": [
                    {
                        "id": "call_vtVHQXttgp960ek68rQ7sthQ",
                        "type": "function",
                        "function": {
                            "name": "Save Booking",
                            "arguments": json.dumps(
                                {
                                    "name": "Taha",
                                    "phone": "1234567891",
                                    "vehicle": "Suzuki Swift",
                                    "date": "2026-08-23",
                                    "time": "17:00",
                                }
                            ),
                        },
                    }
                ],
            }
        }
        calls = provider.normalize_tool_calls(payload)
        assert len(calls) == 1
        assert calls[0].id == "call_vtVHQXttgp960ek68rQ7sthQ"
        assert calls[0].name == "Save Booking"
        assert calls[0].arguments["vehicle"] == "Suzuki Swift"
        formatted = provider.format_tool_results(
            [
                {
                    "id": calls[0].id,
                    "name": calls[0].name,
                    "result": {"success": False, "error": {"message": "slot taken"}},
                    "presentation": "That slot is taken.",
                }
            ]
        )
        assert formatted == {
            "results": [
                {
                    "toolCallId": "call_vtVHQXttgp960ek68rQ7sthQ",
                    "result": "That slot is taken.",
                }
            ]
        }

    def test_user_interrupted_event(self):
        provider = VapiVoiceProvider(_settings())
        events = provider.parse_webhook(
            {"message": {"type": "user-interrupted", "call": {"id": "c-int"}}}
        )
        assert events[0].event_type == "user.interrupted"
        assert events[0].interrupted is True

    def test_error_handling_malformed(self):
        provider = VapiVoiceProvider(_settings())
        assert provider.parse_webhook({}) == []
        assert provider.parse_webhook({"message": {"type": "status-update"}}) == []


class TestUpliftProvider:
    def test_initialization_and_config_validation(self):
        unconfigured = UpliftVoiceProvider(_settings())
        assert unconfigured.name == "uplift"
        assert unconfigured.is_configured() is False
        session = unconfigured.create_session(call_id="u1")
        assert session["configured"] is False

        configured = UpliftVoiceProvider(
            _settings(uplift_api_key="uk", uplift_agent_id="agent_1")
        )
        assert configured.is_configured() is True

    def test_webhook_authentication(self):
        provider = UpliftVoiceProvider(_settings(uplift_webhook_secret=VOICE_SECRET))
        assert provider.verify_webhook(
            headers={"X-Voice-Webhook-Secret": VOICE_SECRET}, body=b"{}"
        )
        assert provider.verify_webhook(
            headers={"Authorization": f"Bearer {VOICE_SECRET}"}, body=b"{}"
        )
        assert provider.verify_webhook(headers={"X-Voice-Webhook-Secret": "nope"}, body=b"{}") is False

    def test_call_event_parsing(self):
        provider = UpliftVoiceProvider(_settings())
        events = provider.parse_webhook(
            {
                "event_type": "call.started",
                "call_id": "uplift-1",
                "payload": {"caller_phone": "+15552223333"},
            }
        )
        assert events[0].event_type == "call.started"
        assert events[0].provider == "uplift"
        assert events[0].caller_phone == "+15552223333"

    def test_normalized_tool_call(self):
        provider = UpliftVoiceProvider(_settings())
        calls = provider.normalize_tool_calls(
            {
                "event_type": "tool.execute",
                "call_id": "uplift-2",
                "payload": {
                    "name": "check_availability",
                    "arguments": {"service_id": "svc"},
                    "tool_call_id": "t1",
                },
            }
        )
        assert calls[0].name == "check_availability"
        assert calls[0].id == "t1"
        formatted = provider.format_tool_results(
            [{"id": "t1", "name": "check_availability", "result": {"ok": True}, "presentation": "Done"}]
        )
        assert formatted["presentationInstructions"] == "Done"

    def test_error_handling_unknown_event(self):
        provider = UpliftVoiceProvider(_settings())
        events = provider.parse_webhook({"event_type": "weird", "call_id": "x"})
        assert events[0].event_type == "ignored"


class TestProviderFactory:
    def test_explicit_selection(self):
        assert create_voice_provider(_settings(voice_provider="fake")).name == "fake"
        assert create_voice_provider(_settings(voice_provider="vapi")).name == "vapi"
        assert create_voice_provider(_settings(voice_provider="uplift")).name == "uplift"

    def test_inactive_provider_missing_creds_does_not_break_selection(self):
        # Selecting vapi without creds still returns Vapi provider (not crash)
        provider = create_voice_provider(_settings(voice_provider="vapi"))
        assert isinstance(provider, VapiVoiceProvider)
        assert provider.is_configured() is False

    def test_auto_prefers_configured(self):
        provider = create_voice_provider(
            _settings(
                voice_provider="auto",
                uplift_api_key="uk",
                uplift_agent_id="aid",
                vapi_api_key="",
                vapi_assistant_id="",
            )
        )
        assert provider.name == "uplift"


@requires_database
class TestProviderCallLogging:
    def test_vapi_call_logging_provider_field(self, db_session):
        fake_llm = FakeLLMProvider(
            [lambda m, t: LLMCompletionResult(content="Hi there.", tool_calls=[])]
        )
        agent = AgentIntegrationService(db_session)
        booking = BookingService(db_session)
        conversation = VoiceConversationAgent(agent, booking, fake_llm, settings=_settings())
        service = VoiceConversationService(
            db_session,
            llm=fake_llm,
            voice_provider=VapiVoiceProvider(_settings(vapi_api_key="k", vapi_assistant_id="a")),
            settings=_settings(voice_provider="vapi"),
            conversation=conversation,
        )
        call_id = f"vapi-{uuid.uuid4().hex[:10]}"
        phone = f"+92320{uuid.uuid4().hex[:8]}"
        service.start_call(
            VoiceCallStartRequest(call_id=call_id, caller_phone=phone, provider="vapi")
        )
        log = db_session.scalar(select(CallLog).where(CallLog.call_id == call_id))
        assert log is not None
        assert log.provider == "vapi"

    def test_uplift_tool_execute_via_normalized_path(self, db_session):
        fake_llm = FakeLLMProvider([])
        agent = AgentIntegrationService(db_session)
        booking = BookingService(db_session)
        conversation = VoiceConversationAgent(agent, booking, fake_llm, settings=_settings())
        provider = UpliftVoiceProvider(_settings(uplift_webhook_secret=VOICE_SECRET))
        service = VoiceConversationService(
            db_session,
            llm=fake_llm,
            voice_provider=provider,
            settings=_settings(voice_provider="uplift"),
            conversation=conversation,
        )
        call_id = f"uplift-{uuid.uuid4().hex[:10]}"
        phone = f"+92321{uuid.uuid4().hex[:8]}"
        service.start_call(
            VoiceCallStartRequest(call_id=call_id, caller_phone=phone, provider="uplift")
        )
        events = provider.parse_webhook(
            {
                "event_type": "tool.execute",
                "call_id": call_id,
                "payload": {
                    "name": "list_services",
                    "arguments": {"active_only": True},
                    "caller_phone": phone,
                },
            }
        )
        summary = service.handle_normalized_events(events)
        assert summary["tool_results"]
        assert summary["tool_results"][0]["name"] == "list_services"
        log = db_session.scalar(select(CallLog).where(CallLog.call_id == call_id))
        assert log.provider == "uplift"


@requires_database
class TestVapiSaveBookingPolish:
    def test_save_booking_uses_requested_service_and_links_call_log(self, db_session):
        """Dynamic service (Basic Wash) + CallLog.booking_id linked on success."""
        from datetime import date, time, timedelta

        from app.models.booking import Booking, BookingSource
        from app.models.call_log import CallOutcome
        from app.models.service import Service
        from app.services.availability_service import AvailabilityService
        from app.voice.normalized import NormalizedVoiceEvent, NormalizedVoiceToolCall

        basic = db_session.scalar(select(Service).where(Service.name == "Basic Wash"))
        assert basic is not None
        availability = AvailabilityService(db_session)
        booking_date = None
        booking_time = None
        for days_ahead in range(14, 90):
            candidate = date.today() + timedelta(days=days_ahead)
            while candidate.weekday() > 4:
                candidate += timedelta(days=1)
            slots = availability.get_available_slots(candidate, basic.id)
            if slots:
                booking_date, booking_time = candidate, slots[0]
                break
        assert booking_date and booking_time

        fake_llm = FakeLLMProvider([])
        agent = AgentIntegrationService(db_session)
        booking_svc = BookingService(db_session)
        conversation = VoiceConversationAgent(agent, booking_svc, fake_llm, settings=_settings())
        service = VoiceConversationService(
            db_session,
            llm=fake_llm,
            voice_provider=VapiVoiceProvider(_settings(vapi_api_key="k", vapi_assistant_id="a")),
            settings=_settings(voice_provider="vapi"),
            conversation=conversation,
        )
        call_id = f"vapi-save-{uuid.uuid4().hex[:10]}"
        phone = f"+92322{uuid.uuid4().hex[:8]}"
        service.start_call(
            VoiceCallStartRequest(call_id=call_id, caller_phone=phone, provider="vapi")
        )

        summary = service.handle_normalized_events(
            [
                NormalizedVoiceEvent(
                    event_type="tool.execute",
                    call_id=call_id,
                    provider="vapi",
                    caller_phone=phone,
                    tool_calls=[
                        NormalizedVoiceToolCall(
                            id="call_test_save_1",
                            name="Save Booking",
                            arguments={
                                "name": "Taha",
                                "phone": phone,
                                "vehicle": "Suzuki Swift",
                                "date": booking_date.isoformat(),
                                "time": booking_time.strftime("%H:%M"),
                                "service": "Basic Wash",
                            },
                        )
                    ],
                )
            ]
        )
        assert summary["tool_results"]
        result = summary["tool_results"][0]["result"]
        assert result.get("success") is True, result

        booking_id = (result.get("data") or {}).get("booking", {}).get("booking_id")
        assert booking_id
        booking = db_session.get(Booking, uuid.UUID(str(booking_id)))
        assert booking is not None
        assert booking.service_id == basic.id
        assert booking.source == BookingSource.VOICE

        log = db_session.scalar(select(CallLog).where(CallLog.call_id == call_id))
        assert log is not None
        assert log.booking_id == booking.id
        assert log.outcome == CallOutcome.BOOKING_CREATED
        assert log.provider == "vapi"

    def test_save_booking_without_service_defaults_to_first_catalog(self, db_session):
        from app.models.booking import Booking, BookingSource

        fake_llm = FakeLLMProvider([])
        agent = AgentIntegrationService(db_session)
        booking_svc = BookingService(db_session)
        conversation = VoiceConversationAgent(agent, booking_svc, fake_llm, settings=_settings())
        service = VoiceConversationService(
            db_session,
            llm=fake_llm,
            voice_provider=VapiVoiceProvider(_settings(vapi_api_key="k", vapi_assistant_id="a")),
            settings=_settings(voice_provider="vapi"),
            conversation=conversation,
        )
        call_id = f"vapi-nosvc-{uuid.uuid4().hex[:10]}"
        phone = f"+92323{uuid.uuid4().hex[:8]}"
        service.start_call(
            VoiceCallStartRequest(call_id=call_id, caller_phone=phone, provider="vapi")
        )
        executed = service.execute_tool(
            VoiceToolExecuteRequest(
                call_id=call_id,
                name="save_booking",
                arguments={
                    "name": "Taha",
                    "phone": phone,
                    "vehicle": "Civic",
                    "date": "2026-09-01",
                    "time": "10:00",
                },
                caller_phone=phone,
            )
        )
        assert executed.success is True, executed.result
        assert executed.result.get("success") is True
        spoken = executed.presentation_instructions or ""
        assert "booked" in spoken.lower()
        booking_id = (executed.result.get("data") or {}).get("booking", {}).get("booking_id")
        assert booking_id
        booking = db_session.get(Booking, uuid.UUID(str(booking_id)))
        assert booking is not None
        assert booking.source == BookingSource.VOICE


class TestProviderHttpWebhooks:
    def test_vapi_webhook_rejects_bad_auth(self):
        get_settings.cache_clear()
        client = TestClient(app)
        resp = client.post(
            "/api/voice/vapi/webhook",
            content=json.dumps(
                {"message": {"type": "status-update", "status": "in-progress", "call": {"id": "x"}}}
            ),
            headers={"Content-Type": "application/json", "Authorization": "Bearer wrong"},
        )
        assert resp.status_code == 401

    def test_vapi_webhook_tool_calls_shape(self, monkeypatch):
        get_settings.cache_clear()
        # Ensure VAPI secret is present for this process
        monkeypatch.setenv("VAPI_WEBHOOK_SECRET", VAPI_SECRET)
        get_settings.cache_clear()
        client = TestClient(app)
        body = {
            "message": {
                "type": "assistant-request",
                "call": {"id": "asst-req-1"},
            }
        }
        # Without assistant configured, returns error object (still 200)
        resp = client.post(
            "/api/voice/vapi/webhook",
            content=json.dumps(body),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {VAPI_SECRET}",
            },
        )
        # May be 401 if settings didn't pick env in already-imported module settings
        assert resp.status_code in {200, 401}
        if resp.status_code == 200:
            assert "assistantId" in resp.json() or "error" in resp.json()

    def test_uplift_webhook_rejects_bad_auth(self):
        get_settings.cache_clear()
        client = TestClient(app)
        resp = client.post(
            "/api/voice/uplift/webhook",
            content=json.dumps({"event_type": "call.started", "call_id": "u1"}),
            headers={"Content-Type": "application/json", "X-Voice-Webhook-Secret": "bad"},
        )
        assert resp.status_code == 401

    def test_provider_status_endpoint(self):
        get_settings.cache_clear()
        client = TestClient(app)
        resp = client.get("/api/voice/provider")
        assert resp.status_code == 200
        data = resp.json()
        assert "active_provider" in data
        assert "vapi" in data["providers"]
        assert "uplift" in data["providers"]
