"""API router integration tests."""

from __future__ import annotations

import uuid
from datetime import date, time, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.models.customer import Customer
from app.models.service import Service
from tests.conftest import requires_database

client = TestClient(app)


def _future_weekday(days_ahead: int = 14) -> date:
    candidate = date.today() + timedelta(days=days_ahead)
    while candidate.weekday() > 4:
        candidate += timedelta(days=1)
    return candidate


def _pick_slot_for_service(service_id: str) -> tuple[date, str]:
    for days_ahead in range(14, 90):
        booking_date = _future_weekday(days_ahead)
        response = client.get(
            "/api/availability",
            params={
                "booking_date": booking_date.isoformat(),
                "service_id": service_id,
            },
        )
        if response.status_code != 200:
            continue
        alternatives = response.json().get("alternatives", [])
        if alternatives:
            return booking_date, alternatives[0]
    raise AssertionError("No available booking slot found")


@requires_database
class TestApiRouters:
    def test_create_and_get_customer(self):
        suffix = uuid.uuid4().hex[:8]
        payload = {
            "name": f"API Customer {suffix}",
            "phone": f"+92-321-{suffix[:4]}{suffix[4:]}",
            "email": f"api-{suffix}@test.sparkle",
        }
        created = client.post("/api/customers", json=payload)
        assert created.status_code == 201
        customer_id = created.json()["id"]

        fetched = client.get(f"/api/customers/{customer_id}")
        assert fetched.status_code == 200
        assert fetched.json()["phone"] == payload["phone"]

    def test_create_vehicle_for_customer(self):
        suffix = uuid.uuid4().hex[:8]
        customer = client.post(
            "/api/customers",
            json={
                "name": f"Vehicle Owner {suffix}",
                "phone": f"+92-322-{suffix[:4]}{suffix[4:]}",
                "email": f"vehicle-{suffix}@test.sparkle",
            },
        )
        customer_id = customer.json()["id"]

        vehicle = client.post(
            f"/api/customers/{customer_id}/vehicles",
            json={
                "vehicle_type": "sedan",
                "make": "Toyota",
                "model": "Corolla",
                "registration_number": f"API-{suffix}",
            },
        )
        assert vehicle.status_code == 201
        assert vehicle.json()["customer_id"] == customer_id

    def test_list_services(self):
        response = client.get("/api/services")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) >= 3

    def test_check_availability(self):
        from app.core.database import SessionLocal

        with SessionLocal() as db:
            service = db.scalar(select(Service).where(Service.active.is_(True)).limit(1))
            assert service is not None

        response = client.get(
            "/api/availability",
            params={
                "booking_date": _future_weekday().isoformat(),
                "service_id": str(service.id),
            },
        )
        assert response.status_code == 200
        assert "available" in response.json()

    def test_create_get_update_delete_booking_and_history(self):
        suffix = uuid.uuid4().hex[:8]
        customer_resp = client.post(
            "/api/customers",
            json={
                "name": f"Booking User {suffix}",
                "phone": f"+92-323-{suffix[:4]}{suffix[4:]}",
                "email": f"booking-{suffix}@test.sparkle",
            },
        )
        customer_id = customer_resp.json()["id"]

        vehicle_resp = client.post(
            f"/api/customers/{customer_id}/vehicles",
            json={
                "vehicle_type": "suv",
                "make": "Kia",
                "model": "Sportage",
                "registration_number": f"BK-{suffix}",
            },
        )
        vehicle_id = vehicle_resp.json()["id"]

        from app.core.database import SessionLocal

        with SessionLocal() as db:
            service = db.scalar(select(Service).where(Service.name == "Basic Wash"))
            assert service is not None

        booking_date, booking_time = _pick_slot_for_service(str(service.id))
        create_resp = client.post(
            "/api/bookings",
            json={
                "customer_id": customer_id,
                "vehicle_id": vehicle_id,
                "service_id": str(service.id),
                "booking_date": booking_date.isoformat(),
                "booking_time": booking_time,
                "source": "dashboard",
                "notes": "API booking",
            },
        )
        assert create_resp.status_code == 201, create_resp.text
        booking_id = create_resp.json()["id"]

        get_resp = client.get(f"/api/bookings/{booking_id}")
        assert get_resp.status_code == 200

        availability_resp = client.get(
            "/api/availability",
            params={
                "booking_date": booking_date.isoformat(),
                "service_id": str(service.id),
            },
        )
        assert availability_resp.status_code == 200
        alternatives = availability_resp.json().get("alternatives", [])
        new_time = next((slot for slot in alternatives if slot != booking_time), booking_time)

        patch_resp = client.patch(
            f"/api/bookings/{booking_id}",
            json={
                "booking_date": booking_date.isoformat(),
                "booking_time": new_time,
            },
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["booking_time"] == new_time

        history_resp = client.get(f"/api/customers/{customer_id}/bookings")
        assert history_resp.status_code == 200
        assert any(item["id"] == booking_id for item in history_resp.json())

        cancel_resp = client.delete(f"/api/bookings/{booking_id}")
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == "cancelled"

    def test_not_found_and_validation_errors(self):
        unknown = str(uuid.uuid4())
        assert client.get(f"/api/customers/{unknown}").status_code == 404
        assert client.get(f"/api/vehicles/{unknown}").status_code == 404
        assert client.get(f"/api/services/{unknown}").status_code == 404
        assert client.get(f"/api/bookings/{unknown}").status_code == 404

        invalid_customer = client.post(
            "/api/customers",
            json={"name": "", "phone": ""},
        )
        assert invalid_customer.status_code == 422

        invalid_booking = client.post(
            "/api/bookings",
            json={"customer_id": unknown},
        )
        assert invalid_booking.status_code == 422
