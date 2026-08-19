"""Booking domain service — single source of truth for booking operations."""

from __future__ import annotations

import uuid
from datetime import date, time

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.exceptions import (
    BookingNotFoundError,
    CustomerNotFoundError,
    InvalidBookingError,
    ServiceNotFoundError,
    SlotUnavailableError,
    VehicleNotFoundError,
)
from app.models.booking import Booking, BookingSource, BookingStatus
from app.models.customer import Customer
from app.models.service import Service
from app.models.vehicle import Vehicle
from app.services.availability_service import AvailabilityService
from app.services.time_utils import is_past_slot

RESCHEDULABLE_STATUSES: frozenset[BookingStatus] = frozenset(
    {BookingStatus.PENDING, BookingStatus.CONFIRMED}
)


class BookingService:
    """Core booking operations used by future APIs and AI tools."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.availability = AvailabilityService(db)

    def get_or_create_customer(
        self,
        *,
        name: str,
        phone: str,
        email: str | None = None,
    ) -> Customer:
        """Find a customer by phone or create a new one."""
        customer = self.db.scalar(select(Customer).where(Customer.phone == phone))
        if customer:
            return customer

        customer = Customer(name=name, phone=phone, email=email)
        self.db.add(customer)
        self.db.flush()
        return customer

    def _get_customer(self, customer_id: uuid.UUID) -> Customer:
        customer = self.db.get(Customer, customer_id)
        if customer is None:
            raise CustomerNotFoundError(f"Customer {customer_id} not found")
        return customer

    def _get_vehicle(self, vehicle_id: uuid.UUID) -> Vehicle:
        vehicle = self.db.get(Vehicle, vehicle_id)
        if vehicle is None:
            raise VehicleNotFoundError(f"Vehicle {vehicle_id} not found")
        return vehicle

    def _get_service(self, service_id: uuid.UUID) -> Service:
        return self.availability.get_service(service_id)

    def _validate_vehicle_belongs_to_customer(
        self,
        vehicle: Vehicle,
        customer_id: uuid.UUID,
    ) -> None:
        if vehicle.customer_id != customer_id:
            raise InvalidBookingError("Vehicle does not belong to the specified customer")

    def _validate_not_past(self, booking_date: date, booking_time: time) -> None:
        if is_past_slot(booking_date, booking_time):
            raise InvalidBookingError("Cannot create or move a booking to a past time")

    def create_booking(
        self,
        *,
        customer_id: uuid.UUID,
        vehicle_id: uuid.UUID,
        service_id: uuid.UUID,
        booking_date: date,
        booking_time: time,
        source: BookingSource = BookingSource.DASHBOARD,
        notes: str | None = None,
        status: BookingStatus = BookingStatus.PENDING,
    ) -> Booking:
        """Create a booking after validating entities, availability, and conflicts."""
        customer = self._get_customer(customer_id)
        vehicle = self._get_vehicle(vehicle_id)
        service = self._get_service(service_id)

        self._validate_vehicle_belongs_to_customer(vehicle, customer.id)
        self._validate_not_past(booking_date, booking_time)

        availability_result = self.availability.check_availability(
            booking_date,
            service.id,
            booking_time,
        )
        if not availability_result.available:
            raise SlotUnavailableError(
                availability_result.message or "Requested slot is unavailable"
            )

        booking = Booking(
            customer_id=customer.id,
            vehicle_id=vehicle.id,
            service_id=service.id,
            booking_date=booking_date,
            booking_time=booking_time,
            status=status,
            source=source,
            notes=notes,
        )
        self.db.add(booking)

        try:
            self.db.flush()
            # Re-check immediately before commit to reduce race-condition windows.
            recheck = self.availability.check_availability(
                booking_date,
                service.id,
                booking_time,
                exclude_booking_id=booking.id,
            )
            if not recheck.available:
                self.db.rollback()
                raise SlotUnavailableError("Requested slot became unavailable")

            self.db.commit()
            self.db.refresh(booking)
            return booking
        except SlotUnavailableError:
            raise
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise SlotUnavailableError("Requested slot is unavailable") from exc

    def get_booking(self, booking_id: uuid.UUID) -> Booking:
        """Return a booking by ID."""
        booking = self.db.get(Booking, booking_id)
        if booking is None:
            raise BookingNotFoundError(f"Booking {booking_id} not found")
        return booking

    def get_bookings(
        self,
        *,
        booking_date: date | None = None,
        status: BookingStatus | None = None,
        customer_id: uuid.UUID | None = None,
        source: BookingSource | None = None,
    ) -> list[Booking]:
        """Return bookings filtered by optional criteria."""
        query = select(Booking).order_by(Booking.booking_date, Booking.booking_time)
        if booking_date is not None:
            query = query.where(Booking.booking_date == booking_date)
        if status is not None:
            query = query.where(Booking.status == status)
        if customer_id is not None:
            query = query.where(Booking.customer_id == customer_id)
        if source is not None:
            query = query.where(Booking.source == source)
        return list(self.db.scalars(query).all())

    def get_customer_bookings(self, customer_id: uuid.UUID) -> list[Booking]:
        """Return all bookings for a customer."""
        self._get_customer(customer_id)
        return self.get_bookings(customer_id=customer_id)

    def reschedule_booking(
        self,
        booking_id: uuid.UUID,
        *,
        new_date: date,
        new_time: time,
    ) -> Booking:
        """Move a booking to a new date/time after availability checks."""
        booking = self.get_booking(booking_id)

        if booking.status not in RESCHEDULABLE_STATUSES:
            raise InvalidBookingError(f"Booking in status '{booking.status.value}' cannot be rescheduled")

        self._validate_not_past(new_date, new_time)

        availability_result = self.availability.check_availability(
            new_date,
            booking.service_id,
            new_time,
            exclude_booking_id=booking.id,
        )
        if not availability_result.available:
            raise SlotUnavailableError(
                availability_result.message or "Requested slot is unavailable"
            )

        booking.booking_date = new_date
        booking.booking_time = new_time

        try:
            self.db.flush()
            recheck = self.availability.check_availability(
                new_date,
                booking.service_id,
                new_time,
                exclude_booking_id=booking.id,
            )
            if not recheck.available:
                self.db.rollback()
                raise SlotUnavailableError("Requested slot became unavailable")

            self.db.commit()
            self.db.refresh(booking)
            return booking
        except SlotUnavailableError:
            raise
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise SlotUnavailableError("Requested slot is unavailable") from exc

    def cancel_booking(self, booking_id: uuid.UUID) -> Booking:
        """Cancel a booking without deleting the record."""
        booking = self.get_booking(booking_id)

        if booking.status == BookingStatus.CANCELLED:
            return booking

        if booking.status == BookingStatus.COMPLETED:
            raise InvalidBookingError("Completed bookings cannot be cancelled")

        booking.status = BookingStatus.CANCELLED
        self.db.commit()
        self.db.refresh(booking)
        return booking
