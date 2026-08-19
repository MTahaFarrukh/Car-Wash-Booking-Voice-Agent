"""Tests for Phase 5 agent integration layer."""

from __future__ import annotations

import uuid
from datetime import date, time, timedelta

from sqlalchemy import select

from app.agent import AgentIntegrationService, get_tool_definitions
from app.models.customer import Customer
from app.models.service import Service
from app.schemas.agent import (
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
from app.services.availability_service import AvailabilityService
from tests.conftest import requires_database


def _future_weekday(days_ahead: int = 14) -> date:
    candidate = date.today() + timedelta(days=days_ahead)
    while candidate.weekday() > 4:
        candidate += timedelta(days=1)
    return candidate


def _pick_available_slots(db_session, service_id, *, min_slots: int = 1) -> tuple[date, list[time]]:
    availability = AvailabilityService(db_session)
    for days_ahead in range(14, 90):
        booking_date = _future_weekday(days_ahead)
        slots = availability.get_available_slots(booking_date, service_id)
        if len(slots) >= min_slots:
            return booking_date, slots
    raise AssertionError("No suitable available slots found")


@requires_database
class TestAgentTools:
    def test_tool_definitions_exist(self, db_session):
        definitions = get_tool_definitions()
        assert len(definitions) >= 10
        assert any(item.name == "create_booking" for item in definitions)

    def test_customer_creation_and_lookup(self, db_session):
        agent = AgentIntegrationService(db_session)
        suffix = uuid.uuid4().hex[:8]
        create = agent.find_or_create_customer(
            CustomerToolInput(
                name=f"Agent Customer {suffix}",
                phone=f"+92-324-{suffix[:4]}{suffix[4:]}",
                email=f"agent-{suffix}@test.sparkle",
            )
        )
        assert create.success
        customer_id = create.data["customer_id"]

        lookup = agent.get_customer(CustomerLookupInput(customer_id=customer_id))
        assert lookup.success
        assert lookup.data["customer_id"] == customer_id

    def test_vehicle_creation(self, db_session):
        agent = AgentIntegrationService(db_session)
        customer = db_session.scalar(select(Customer).limit(1))
        result = agent.create_vehicle(
            VehicleCreateToolInput(
                customer_id=customer.id,
                vehicle_type="sedan",
                make="Honda",
                model="Civic",
                registration_number=f"AG-{uuid.uuid4().hex[:6]}",
            )
        )
        assert result.success
        assert result.data["customer_id"] == str(customer.id)

    def test_service_listing_and_availability(self, db_session):
        agent = AgentIntegrationService(db_session)
        services = agent.list_services(ServicesListInput(active_only=True))
        assert services.success
        assert len(services.data["services"]) >= 1

        service_id = services.data["services"][0]["service_id"]
        availability = agent.check_availability(
            AvailabilityToolInput(
                booking_date=_future_weekday(),
                service_id=service_id,
            )
        )
        assert availability.success
        assert "available" in availability.data

    def test_successful_booking_and_lookup(self, db_session):
        agent = AgentIntegrationService(db_session)
        customer = db_session.scalar(select(Customer).limit(1))
        service = db_session.scalar(select(Service).where(Service.active.is_(True)).limit(1))
        vehicles = agent.get_customer_vehicles(VehicleLookupInput(customer_id=customer.id))
        assert vehicles.success
        vehicle_id = vehicles.data["vehicles"][0]["vehicle_id"]
        booking_date, slots = _pick_available_slots(db_session, service.id, min_slots=1)

        create = agent.create_booking(
            BookingCreateToolInput(
                customer_id=customer.id,
                vehicle_id=vehicle_id,
                service_id=service.id,
                booking_date=booking_date,
                booking_time=slots[0],
            )
        )
        assert create.success
        booking_id = create.data["booking"]["booking_id"]

        lookup = agent.get_booking(BookingLookupInput(booking_id=booking_id))
        assert lookup.success
        assert lookup.data["booking"]["booking_id"] == booking_id

    def test_unavailable_slot_and_invalid_entities(self, db_session):
        agent = AgentIntegrationService(db_session)
        customer = db_session.scalar(select(Customer).limit(1))
        service = db_session.scalar(select(Service).where(Service.active.is_(True)).limit(1))
        vehicles = agent.get_customer_vehicles(VehicleLookupInput(customer_id=customer.id))
        vehicle_id = vehicles.data["vehicles"][0]["vehicle_id"]
        booking_date, slots = _pick_available_slots(db_session, service.id, min_slots=1)

        first = agent.create_booking(
            BookingCreateToolInput(
                customer_id=customer.id,
                vehicle_id=vehicle_id,
                service_id=service.id,
                booking_date=booking_date,
                booking_time=slots[0],
            )
        )
        assert first.success

        second = agent.create_booking(
            BookingCreateToolInput(
                customer_id=customer.id,
                vehicle_id=vehicle_id,
                service_id=service.id,
                booking_date=booking_date,
                booking_time=slots[0],
            )
        )
        # duplicate protection returns existing booking as success
        assert second.success
        assert second.data["duplicate"] is True

        invalid_customer = agent.get_customer(CustomerLookupInput(customer_id=uuid.uuid4()))
        assert not invalid_customer.success
        assert invalid_customer.error.error_code == "CUSTOMER_NOT_FOUND"

        invalid_vehicle_booking = agent.create_booking(
            BookingCreateToolInput(
                customer_id=customer.id,
                vehicle_id=uuid.uuid4(),
                service_id=service.id,
                booking_date=_future_weekday(35),
                booking_time=time(10, 0),
            )
        )
        assert not invalid_vehicle_booking.success
        assert invalid_vehicle_booking.error.error_code == "VEHICLE_NOT_FOUND"

        invalid_service_booking = agent.create_booking(
            BookingCreateToolInput(
                customer_id=customer.id,
                vehicle_id=vehicle_id,
                service_id=uuid.uuid4(),
                booking_date=_future_weekday(35),
                booking_time=time(10, 30),
            )
        )
        assert not invalid_service_booking.success
        assert invalid_service_booking.error.error_code == "SERVICE_NOT_FOUND"

    def test_reschedule_and_cancel(self, db_session):
        agent = AgentIntegrationService(db_session)
        customer = db_session.scalar(select(Customer).limit(1))
        service = db_session.scalar(select(Service).where(Service.active.is_(True)).limit(1))
        vehicles = agent.get_customer_vehicles(VehicleLookupInput(customer_id=customer.id))
        vehicle_id = vehicles.data["vehicles"][0]["vehicle_id"]

        create = agent.create_booking(
            BookingCreateToolInput(
                customer_id=customer.id,
                vehicle_id=vehicle_id,
                service_id=service.id,
                booking_date=_future_weekday(42),
                booking_time=time(15, 0),
            )
        )
        assert create.success
        booking_id = create.data["booking"]["booking_id"]

        reschedule = agent.reschedule_booking(
            BookingRescheduleToolInput(
                booking_id=booking_id,
                booking_date=_future_weekday(42),
                booking_time=time(16, 0),
            )
        )
        assert reschedule.success

        cancel = agent.cancel_booking(BookingCancelToolInput(booking_id=booking_id))
        assert cancel.success
        assert cancel.data["new_status"] == "cancelled"

        cancel_again = agent.cancel_booking(BookingCancelToolInput(booking_id=booking_id))
        assert not cancel_again.success
        assert cancel_again.error.error_code == "BOOKING_ALREADY_CANCELLED"

    def test_invalid_booking_lookup(self, db_session):
        agent = AgentIntegrationService(db_session)
        result = agent.get_booking(BookingLookupInput(booking_id=uuid.uuid4()))
        assert not result.success
        assert result.error.error_code == "BOOKING_NOT_FOUND"
