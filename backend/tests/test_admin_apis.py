"""Phase 9 admin read API tests."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.models.call_log import CallLog, CallOutcome
from app.models.customer import Customer
from app.models.whatsapp_message import WhatsAppProcessedMessage
from tests.conftest import requires_database

client = TestClient(app)


@requires_database
class TestAdminApis:
    def test_list_customers(self, db_session):
        phone = f"+9299{uuid.uuid4().hex[:8]}"
        db_session.add(Customer(name="Phase9 Customer", phone=phone))
        db_session.commit()
        resp = client.get("/api/customers", params={"q": "Phase9"})
        assert resp.status_code == 200
        assert any(row["phone"] == phone for row in resp.json())

    def test_admin_status_no_secrets(self):
        resp = client.get("/api/admin/status")
        assert resp.status_code == 200
        data = resp.json()
        blob = str(data).lower()
        assert "api_key" not in blob
        assert "secret" not in blob or "configured" in blob
        assert "database" in data
        assert "voice" in data

    def test_call_logs_and_whatsapp_activity(self, db_session):
        call_id = f"admin-call-{uuid.uuid4().hex[:8]}"
        db_session.add(
            CallLog(
                call_id=call_id,
                provider="vapi",
                phone="+15550001111",
                outcome=CallOutcome.NO_BOOKING,
            )
        )
        db_session.add(
            WhatsAppProcessedMessage(
                message_id=f"wamid-{uuid.uuid4().hex[:8]}",
                sender_id="923001112233",
                response_message="Hello from Sparkle",
            )
        )
        db_session.commit()

        logs = client.get("/api/admin/call-logs")
        assert logs.status_code == 200
        assert any(row["call_id"] == call_id for row in logs.json())

        activity = client.get("/api/admin/whatsapp/activity")
        assert activity.status_code == 200
        assert any("Hello from Sparkle" in row["response_message"] for row in activity.json())

    def test_admin_bookings_enriched(self, db_session):
        resp = client.get("/api/admin/bookings", params={"limit": 5})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
