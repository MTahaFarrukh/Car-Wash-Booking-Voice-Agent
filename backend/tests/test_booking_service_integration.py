"""Integration tests for booking and availability services."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta

import pytest
from sqlalchemy import select, update

from app.exceptions import (
    BookingNotFoundError,
    InvalidBookingError,
    SlotUnavailableError,
)
from app.models import Availability, Booking, BookingSource, BookingStatus, Customer, Service, Vehicle
from app.services.availability_service import AvailabilityService
from app.services.booking_service import BookingService
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
    pytest.skip("No suitable available slots found in date range")


@requires_database
class TestBookingServiceIntegration:
    def test_create_booking_when_slot_is_free(self, db_session):
        service = BookingService(db_session)
        availability = AvailabilityService(db_session)

        customer = db_session.scalar(select(Customer).limit(1))
        vehicle = db_session.scalar(select(Vehicle).where(Vehicle.customer_id == customer.id).limit(1))
        wash = db_session.scalar(select(Service).where(Service.name == "Basic Wash"))

        booking_date = _future_weekday()
        booking_time = time(13, 0)
        result = availability.check_availability(booking_date, wash.id, booking_time)
        if not result.available:
            pytest.skip("Selected slot unavailable in seeded database")

        booking = service.create_booking(
            customer_id=customer.id,
            vehicle_id=vehicle.id,
            service_id=wash.id,
            booking_date=booking_date,
            booking_time=booking_time,
            source=BookingSource.VOICE,
        )
        assert booking.id is not None
        assert booking.status == BookingStatus.PENDING

    def test_create_booking_fails_on_conflict(self, db_session):
        service = BookingService(db_session)
        customer = db_session.scalar(select(Customer).limit(1))
        vehicle = db_session.scalar(select(Vehicle).where(Vehicle.customer_id == customer.id).limit(1))
        wash = db_session.scalar(select(Service).where(Service.name == "Premium Wash"))

        booking_date, slots = _pick_available_slots(db_session, wash.id, min_slots=1)
        booking_time = slots[0]

        service.create_booking(
            customer_id=customer.id,
            vehicle_id=vehicle.id,
            service_id=wash.id,
            booking_date=booking_date,
            booking_time=booking_time,
        )

        with pytest.raises(SlotUnavailableError):
            service.create_booking(
                customer_id=customer.id,
                vehicle_id=vehicle.id,
                service_id=wash.id,
                booking_date=booking_date,
                booking_time=booking_time,
            )

    def test_reschedule_to_available_slot(self, db_session):
        service = BookingService(db_session)
        customer = db_session.scalar(select(Customer).limit(1))
        vehicle = db_session.scalar(select(Vehicle).where(Vehicle.customer_id == customer.id).limit(1))
        wash = db_session.scalar(select(Service).where(Service.name == "Basic Wash"))

        booking_date, slots = _pick_available_slots(db_session, wash.id, min_slots=2)
        booking = service.create_booking(
            customer_id=customer.id,
            vehicle_id=vehicle.id,
            service_id=wash.id,
            booking_date=booking_date,
            booking_time=slots[0],
        )

        updated = service.reschedule_booking(booking.id, new_date=booking_date, new_time=slots[1])
        assert updated.booking_time == slots[1]

    def test_reschedule_to_occupied_slot_fails(self, db_session):
        service = BookingService(db_session)
        customer = db_session.scalar(select(Customer).limit(1))
        vehicle = db_session.scalar(select(Vehicle).where(Vehicle.customer_id == customer.id).limit(1))
        wash = db_session.scalar(select(Service).where(Service.name == "Basic Wash"))

        booking_date, slots = _pick_available_slots(db_session, wash.id, min_slots=2)
        first = service.create_booking(
            customer_id=customer.id,
            vehicle_id=vehicle.id,
            service_id=wash.id,
            booking_date=booking_date,
            booking_time=slots[0],
        )
        second = service.create_booking(
            customer_id=customer.id,
            vehicle_id=vehicle.id,
            service_id=wash.id,
            booking_date=booking_date,
            booking_time=slots[1],
        )

        with pytest.raises(SlotUnavailableError):
            service.reschedule_booking(second.id, new_date=booking_date, new_time=slots[0])

        db_session.refresh(first)

    def test_cancel_booking_changes_status(self, db_session):
        service = BookingService(db_session)
        customer = db_session.scalar(select(Customer).limit(1))
        vehicle = db_session.scalar(select(Vehicle).where(Vehicle.customer_id == customer.id).limit(1))
        wash = db_session.scalar(select(Service).where(Service.name == "Basic Wash"))

        booking = service.create_booking(
            customer_id=customer.id,
            vehicle_id=vehicle.id,
            service_id=wash.id,
            booking_date=_future_weekday(42),
            booking_time=time(13, 30),
        )

        cancelled = service.cancel_booking(booking.id)
        assert cancelled.status == BookingStatus.CANCELLED
        assert db_session.get(Booking, booking.id) is not None

    def test_get_or_create_customer_is_idempotent(self, db_session):
        service = BookingService(db_session)
        phone = "+92-300-9999999"
        first = service.get_or_create_customer(name="Test User", phone=phone)
        second = service.get_or_create_customer(name="Other Name", phone=phone)
        assert first.id == second.id

    def test_vehicle_customer_validation(self, db_session):
        service = BookingService(db_session)
        customers = db_session.scalars(select(Customer).limit(2)).all()
        if len(customers) < 2:
            pytest.skip("Need at least two seeded customers")

        wrong_vehicle = db_session.scalar(
            select(Vehicle).where(Vehicle.customer_id == customers[1].id).limit(1)
        )
        wash = db_session.scalar(select(Service).where(Service.name == "Basic Wash"))

        with pytest.raises(InvalidBookingError):
            service.create_booking(
                customer_id=customers[0].id,
                vehicle_id=wrong_vehicle.id,
                service_id=wash.id,
                booking_date=_future_weekday(49),
                booking_time=time(15, 30),
            )

    def test_past_booking_is_rejected(self, db_session):
        service = BookingService(db_session)
        customer = db_session.scalar(select(Customer).limit(1))
        vehicle = db_session.scalar(select(Vehicle).where(Vehicle.customer_id == customer.id).limit(1))
        wash = db_session.scalar(select(Service).where(Service.name == "Basic Wash"))

        with pytest.raises(InvalidBookingError):
            service.create_booking(
                customer_id=customer.id,
                vehicle_id=vehicle.id,
                service_id=wash.id,
                booking_date=date.today() - timedelta(days=1),
                booking_time=time(10, 0),
            )

    def test_get_booking_not_found(self, db_session):
        service = BookingService(db_session)
        with pytest.raises(BookingNotFoundError):
            service.get_booking(uuid.uuid4())

    def test_cancelled_booking_does_not_block_slot(self, db_session):
        availability = AvailabilityService(db_session)
        service = BookingService(db_session)
        customer = db_session.scalar(select(Customer).limit(1))
        vehicle = db_session.scalar(select(Vehicle).where(Vehicle.customer_id == customer.id).limit(1))
        wash = db_session.scalar(select(Service).where(Service.name == "Basic Wash"))

        booking_date = _future_weekday(56)
        slot = time(16, 0)
        booking = service.create_booking(
            customer_id=customer.id,
            vehicle_id=vehicle.id,
            service_id=wash.id,
            booking_date=booking_date,
            booking_time=slot,
        )
        service.cancel_booking(booking.id)

        result = availability.check_availability(booking_date, wash.id, slot)
        assert result.available

    def test_inactive_day_returns_no_slots(self, db_session):
        availability = AvailabilityService(db_session)
        wash = db_session.scalar(select(Service).where(Service.name == "Basic Wash"))

        # Monday=0 in seed; use a weekday with no availability row by using day 7 equivalent
        # Simulate closed day: no active availability row matches an impossible query path.
        closed_date = date(2026, 1, 1)  # arbitrary date
        db_session.execute(update(Availability).values(active=False))
        db_session.commit()

        slots = availability.get_available_slots(closed_date, wash.id)
        assert slots == []

        db_session.execute(update(Availability).values(active=True))
        db_session.commit()
