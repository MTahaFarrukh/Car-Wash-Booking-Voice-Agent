"""Business availability and slot generation service."""

from __future__ import annotations

import uuid
from datetime import date, time

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.exceptions import BusinessClosedError, ServiceNotFoundError, SlotUnavailableError
from app.models.availability import Availability
from app.models.booking import Booking
from app.models.service import Service
from app.schemas.booking import AvailabilityCheckResult
from app.services.slot_engine import (
    BLOCKING_STATUSES,
    OccupiedInterval,
    filter_available_slots,
    find_alternative_slots,
    generate_candidate_slots,
    is_slot_free,
    requested_time_is_valid,
)
from app.services.time_utils import date_weekday, is_past_slot


class AvailabilityService:
    """Calculates available booking slots from business rules and existing bookings."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_service(self, service_id: uuid.UUID) -> Service:
        service = self.db.get(Service, service_id)
        if service is None:
            raise ServiceNotFoundError(f"Service {service_id} not found")
        if not service.active:
            raise ServiceNotFoundError(f"Service {service_id} is inactive")
        return service

    def get_availability_for_date(self, booking_date: date) -> Availability | None:
        day_of_week = date_weekday(booking_date)
        return self.db.scalar(
            select(Availability).where(
                Availability.day_of_week == day_of_week,
                Availability.active.is_(True),
            )
        )

    def get_occupied_intervals(
        self,
        booking_date: date,
        *,
        exclude_booking_id: uuid.UUID | None = None,
    ) -> list[OccupiedInterval]:
        """Load blocking bookings for a date with their service durations."""
        query = (
            select(Booking)
            .options(joinedload(Booking.service))
            .where(
                Booking.booking_date == booking_date,
                Booking.status.in_(BLOCKING_STATUSES),
            )
        )
        if exclude_booking_id is not None:
            query = query.where(Booking.id != exclude_booking_id)

        bookings = self.db.scalars(query).unique().all()
        return [
            OccupiedInterval(start=booking.booking_time, duration_minutes=booking.service.duration_minutes)
            for booking in bookings
        ]

    def get_available_slots(
        self,
        booking_date: date,
        service_id: uuid.UUID,
        *,
        exclude_booking_id: uuid.UUID | None = None,
    ) -> list[time]:
        """Return all available slot start times for a date and service."""
        availability = self.get_availability_for_date(booking_date)
        if availability is None:
            return []

        service = self.get_service(service_id)
        occupied = self.get_occupied_intervals(booking_date, exclude_booking_id=exclude_booking_id)

        candidates = generate_candidate_slots(
            availability.opening_time,
            availability.closing_time,
            availability.slot_duration_minutes,
            service.duration_minutes,
        )
        available = filter_available_slots(candidates, service.duration_minutes, occupied)
        return available

    def check_availability(
        self,
        booking_date: date,
        service_id: uuid.UUID,
        requested_time: time | None = None,
        *,
        exclude_booking_id: uuid.UUID | None = None,
    ) -> AvailabilityCheckResult:
        """Check whether a slot is available and return structured alternatives."""
        if is_past_slot(booking_date, requested_time) if requested_time else is_past_date(booking_date):
            return AvailabilityCheckResult(
                available=False,
                requested_time=requested_time,
                alternatives=[],
                message="Cannot book in the past",
            )

        availability = self.get_availability_for_date(booking_date)
        if availability is None:
            return AvailabilityCheckResult(
                available=False,
                requested_time=requested_time,
                alternatives=[],
                message="Business is closed on this day",
            )

        service = self.get_service(service_id)
        occupied = self.get_occupied_intervals(booking_date, exclude_booking_id=exclude_booking_id)
        candidates = generate_candidate_slots(
            availability.opening_time,
            availability.closing_time,
            availability.slot_duration_minutes,
            service.duration_minutes,
        )
        available_slots = filter_available_slots(candidates, service.duration_minutes, occupied)

        if requested_time is None:
            return AvailabilityCheckResult(
                available=len(available_slots) > 0,
                requested_time=None,
                alternatives=available_slots,
                message=None if available_slots else "No available slots for this date",
            )

        if not requested_time_is_valid(
            requested_time,
            service.duration_minutes,
            availability.opening_time,
            availability.closing_time,
        ):
            alternatives = find_alternative_slots(requested_time, available_slots)
            return AvailabilityCheckResult(
                available=False,
                requested_time=requested_time,
                alternatives=alternatives,
                message="Requested time is outside business hours",
            )

        if not is_slot_free(requested_time, service.duration_minutes, occupied):
            alternatives = find_alternative_slots(requested_time, available_slots)
            return AvailabilityCheckResult(
                available=False,
                requested_time=requested_time,
                alternatives=alternatives,
                message="Requested slot is unavailable",
            )

        return AvailabilityCheckResult(
            available=True,
            requested_time=requested_time,
            alternatives=[],
        )

    def assert_slot_available(
        self,
        booking_date: date,
        service_id: uuid.UUID,
        booking_time: time,
        *,
        exclude_booking_id: uuid.UUID | None = None,
    ) -> None:
        """Raise BusinessClosedError or let BookingService handle unavailability."""
        availability = self.get_availability_for_date(booking_date)
        if availability is None:
            raise BusinessClosedError("Business is closed on this day")

        result = self.check_availability(
            booking_date,
            service_id,
            booking_time,
            exclude_booking_id=exclude_booking_id,
        )
        if not result.available:
            raise SlotUnavailableError(result.message or "Requested slot is unavailable")


def is_past_date(booking_date: date) -> bool:
    """Return True when the entire date is in the past."""
    from datetime import datetime

    return booking_date < datetime.now().date()
