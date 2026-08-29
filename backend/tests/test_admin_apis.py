"""Phase 9 admin read API tests (auth required — Phase 10A)."""

from __future__ import annotations

import uuid
from datetime import date, time, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.models.admin_user import AdminUser
from app.models.booking import Booking, BookingSource, BookingStatus
from app.models.call_log import CallLog, CallOutcome
from app.models.customer import Customer
from app.models.service import Service
from app.models.vehicle import Vehicle
from app.models.whatsapp_message import WhatsAppProcessedMessage
from tests.conftest import requires_database

client = TestClient(app)


def _auth_headers(db_session) -> dict[str, str]:
    auth_id = uuid.uuid4()
    email = f"admin-api-{uuid.uuid4().hex[:8]}@sparkle.test"
    db_session.add(AdminUser(auth_user_id=auth_id, email=email, role="ADMIN", is_active=True))
    db_session.commit()

    def _fake_verify(token: str, settings):
        return {"id": str(auth_id), "email": email}

    patcher = patch("app.auth.deps.verify_supabase_access_token", side_effect=_fake_verify)
    patcher.start()
    # Store on function for cleanup if needed; tests are short-lived
    _auth_headers._patcher = patcher  # type: ignore[attr-defined]
    return {"Authorization": "Bearer test-admin-token"}


@requires_database
class TestAdminApis:
    def test_list_customers(self, db_session):
        phone = f"+9299{uuid.uuid4().int % 10_000_000:08d}"
        db_session.add(Customer(name="Phase9 Customer", phone=phone))
        db_session.commit()
        resp = client.get("/api/customers", params={"q": "Phase9"})
        assert resp.status_code == 200
        assert any(row["phone"] == phone for row in resp.json())

    def test_admin_status_no_secrets(self, db_session):
        headers = _auth_headers(db_session)
        try:
            resp = client.get("/api/admin/status", headers=headers)
            assert resp.status_code == 200
            data = resp.json()
            blob = str(data).lower()
            assert "api_key" not in blob
            assert "secret" not in blob or "configured" in blob
            assert "database" in data
            assert "voice" in data
        finally:
            getattr(_auth_headers, "_patcher", None) and _auth_headers._patcher.stop()  # type: ignore[attr-defined]

    def test_call_logs_and_whatsapp_activity(self, db_session):
        headers = _auth_headers(db_session)
        try:
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

            logs = client.get("/api/admin/call-logs", headers=headers)
            assert logs.status_code == 200
            assert any(row["call_id"] == call_id for row in logs.json())

            activity = client.get("/api/admin/whatsapp/activity", headers=headers)
            assert activity.status_code == 200
            assert any("Hello from Sparkle" in row["response_message"] for row in activity.json())
        finally:
            getattr(_auth_headers, "_patcher", None) and _auth_headers._patcher.stop()  # type: ignore[attr-defined]

    def test_admin_bookings_enriched(self, db_session):
        headers = _auth_headers(db_session)
        try:
            resp = client.get("/api/admin/bookings", params={"limit": 5}, headers=headers)
            assert resp.status_code == 200
            assert isinstance(resp.json(), list)
        finally:
            getattr(_auth_headers, "_patcher", None) and _auth_headers._patcher.stop()  # type: ignore[attr-defined]

    def test_admin_notifications_and_acknowledge(self, db_session):
        headers = _auth_headers(db_session)
        try:
            phone = f"+9298{uuid.uuid4().int % 10_000_000:08d}"
            customer = Customer(name="Notify Test", phone=phone)
            db_session.add(customer)
            db_session.flush()
            service = db_session.scalars(select(Service).limit(1)).first()
            assert service is not None
            vehicle = Vehicle(
                customer_id=customer.id,
                vehicle_type="car",
                make="Honda",
                model="City",
                registration_number="TEST-1",
            )
            db_session.add(vehicle)
            db_session.flush()
            booking = Booking(
                customer_id=customer.id,
                vehicle_id=vehicle.id,
                service_id=service.id,
                booking_date=date.today() + timedelta(days=2),
                booking_time=time(10, 0),
                status=BookingStatus.PENDING,
                source=BookingSource.VOICE,
                admin_acknowledged_at=None,
            )
            db_session.add(booking)
            db_session.commit()

            count_before = client.get("/api/admin/notifications/count", headers=headers)
            assert count_before.status_code == 200
            assert count_before.json()["count"] >= 1

            listed = client.get("/api/admin/notifications", headers=headers)
            assert listed.status_code == 200
            assert any(row["id"] == str(booking.id) for row in listed.json())

            ack = client.post(f"/api/admin/bookings/{booking.id}/acknowledge", headers=headers)
            assert ack.status_code == 200
            body = ack.json()
            assert body["status"] == "confirmed"
            assert body["admin_acknowledged_at"] is not None

            count_after = client.get("/api/admin/notifications/count", headers=headers)
            assert count_after.json()["count"] == count_before.json()["count"] - 1
        finally:
            getattr(_auth_headers, "_patcher", None) and _auth_headers._patcher.stop()  # type: ignore[attr-defined]
