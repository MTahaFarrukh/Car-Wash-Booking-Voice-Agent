"""AI agent integration layer built on existing domain services."""

from __future__ import annotations

import uuid
from datetime import date, time

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.exceptions import (
    BookingNotFoundError,
    CustomerNotFoundError,
    InvalidBookingError,
    ServiceNotFoundError,
    SlotUnavailableError,
    VehicleNotFoundError,
)
from app.models.booking import Booking, BookingStatus
from app.schemas.agent import (
    AgentError,
    AgentResult,
    BookingData,
    BookingLookupInput,
    BookingRescheduleToolInput,
    BookingCancelToolInput,
    BookingCreateToolInput,
    CustomerLookupInput,
    CustomerToolInput,
    ServicesListInput,
    AvailabilityToolInput,
    VehicleCreateToolInput,
    VehicleLookupInput,
)
from app.services import (
    AvailabilityService,
    BookingService,
    CustomerVehicleService,
    ServiceCatalogService,
)


class AgentIntegrationService:
    """Provider-agnostic tool handlers for conversational agents."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.booking_service = BookingService(db)
        self.availability_service = AvailabilityService(db)
        self.customer_vehicle_service = CustomerVehicleService(db)
        self.service_catalog_service = ServiceCatalogService(db)

    def _ok(self, data: dict) -> AgentResult:
        return AgentResult(success=True, data=data, error=None)

    def _error(
        self,
        *,
        error_code: AgentError.__annotations__["error_code"],
        message: str,
        retryable: bool = False,
        suggested_action: str | None = None,
    ) -> AgentResult:
        return AgentResult(
            success=False,
            data=None,
            error=AgentError(
                error_code=error_code,
                message=message,
                retryable=retryable,
                suggested_action=suggested_action,
            ),
        )

    def _map_exception(self, exc: Exception) -> AgentResult:
        if isinstance(exc, CustomerNotFoundError):
            return self._error(error_code="CUSTOMER_NOT_FOUND", message=str(exc), suggested_action="Provide a valid customer")
        if isinstance(exc, VehicleNotFoundError):
            return self._error(error_code="VEHICLE_NOT_FOUND", message=str(exc), suggested_action="Provide a valid vehicle")
        if isinstance(exc, ServiceNotFoundError):
            return self._error(error_code="SERVICE_NOT_FOUND", message=str(exc), suggested_action="Choose an active service")
        if isinstance(exc, BookingNotFoundError):
            return self._error(error_code="BOOKING_NOT_FOUND", message=str(exc), suggested_action="Provide a valid booking ID")
        if isinstance(exc, SlotUnavailableError):
            return self._error(
                error_code="SLOT_UNAVAILABLE",
                message=str(exc),
                retryable=True,
                suggested_action="Ask for another time slot",
            )
        if isinstance(exc, InvalidBookingError):
            return self._error(
                error_code="INVALID_BOOKING_TIME",
                message=str(exc),
                suggested_action="Check booking date/time and related entities",
            )
        return self._error(error_code="UNKNOWN_ERROR", message="Unexpected error", retryable=True)

    @staticmethod
    def _booking_to_data(booking: Booking) -> BookingData:
        return BookingData(
            booking_id=booking.id,
            customer_id=booking.customer_id,
            vehicle_id=booking.vehicle_id,
            service_id=booking.service_id,
            booking_date=booking.booking_date,
            booking_time=booking.booking_time,
            status=booking.status,
            source=booking.source,
            notes=booking.notes,
        )

    def find_or_create_customer(self, payload: CustomerToolInput) -> AgentResult:
        customer = self.customer_vehicle_service.find_or_create_customer(**payload.model_dump())
        return self._ok(
            {
                "customer_id": str(customer.id),
                "name": customer.name,
                "phone": customer.phone,
                "email": customer.email,
            }
        )

    def get_customer(self, payload: CustomerLookupInput) -> AgentResult:
        try:
            if payload.customer_id is not None:
                customer = self.customer_vehicle_service.get_customer(payload.customer_id)
            elif payload.phone is not None:
                customer = self.customer_vehicle_service.find_customer_by_phone(payload.phone)
                if customer is None:
                    raise CustomerNotFoundError(f"Customer with phone {payload.phone} not found")
            else:
                return self._error(
                    error_code="VALIDATION_ERROR",
                    message="Either customer_id or phone is required",
                    suggested_action="Provide one identifier",
                )
            return self._ok(
                {
                    "customer_id": str(customer.id),
                    "name": customer.name,
                    "phone": customer.phone,
                    "email": customer.email,
                }
            )
        except Exception as exc:
            return self._map_exception(exc)

    def create_vehicle(self, payload: VehicleCreateToolInput) -> AgentResult:
        try:
            vehicle = self.customer_vehicle_service.create_vehicle(payload.customer_id, **payload.model_dump(exclude={"customer_id"}))
            return self._ok(
                {
                    "vehicle_id": str(vehicle.id),
                    "customer_id": str(vehicle.customer_id),
                    "vehicle_type": vehicle.vehicle_type,
                    "make": vehicle.make,
                    "model": vehicle.model,
                    "registration_number": vehicle.registration_number,
                }
            )
        except Exception as exc:
            return self._map_exception(exc)

    def get_customer_vehicles(self, payload: VehicleLookupInput) -> AgentResult:
        try:
            if payload.customer_id is None:
                return self._error(
                    error_code="VALIDATION_ERROR",
                    message="customer_id is required",
                    suggested_action="Provide customer_id",
                )
            vehicles = self.customer_vehicle_service.list_customer_vehicles(payload.customer_id)
            return self._ok(
                {
                    "customer_id": str(payload.customer_id),
                    "vehicles": [
                        {
                            "vehicle_id": str(vehicle.id),
                            "vehicle_type": vehicle.vehicle_type,
                            "make": vehicle.make,
                            "model": vehicle.model,
                            "registration_number": vehicle.registration_number,
                        }
                        for vehicle in vehicles
                    ],
                }
            )
        except Exception as exc:
            return self._map_exception(exc)

    def list_services(self, payload: ServicesListInput) -> AgentResult:
        services = self.service_catalog_service.list_services(active_only=payload.active_only)
        return self._ok(
            {
                "services": [
                    {
                        "service_id": str(service.id),
                        "name": service.name,
                        "description": service.description,
                        "duration_minutes": service.duration_minutes,
                        "price": str(service.price),
                        "active": service.active,
                    }
                    for service in services
                ]
            }
        )

    def check_availability(self, payload: AvailabilityToolInput) -> AgentResult:
        try:
            service = self.service_catalog_service.get_service(payload.service_id)
            result = self.availability_service.check_availability(
                payload.booking_date, payload.service_id, payload.requested_time
            )
            return self._ok(
                {
                    "requested_date": payload.booking_date.isoformat(),
                    "service": {"service_id": str(service.id), "name": service.name, "duration_minutes": service.duration_minutes},
                    "requested_time": payload.requested_time.isoformat() if payload.requested_time else None,
                    "available": result.available,
                    "available_slots": [slot.isoformat() for slot in result.alternatives],
                    "message": result.message,
                }
            )
        except Exception as exc:
            return self._map_exception(exc)

    def _find_duplicate_booking(self, payload: BookingCreateToolInput) -> Booking | None:
        statuses = [BookingStatus.PENDING, BookingStatus.CONFIRMED]
        return self.db.scalar(
            select(Booking).where(
                and_(
                    Booking.customer_id == payload.customer_id,
                    Booking.vehicle_id == payload.vehicle_id,
                    Booking.service_id == payload.service_id,
                    Booking.booking_date == payload.booking_date,
                    Booking.booking_time == payload.booking_time,
                    Booking.status.in_(statuses),
                )
            )
        )

    def create_booking(self, payload: BookingCreateToolInput) -> AgentResult:
        duplicate = self._find_duplicate_booking(payload)
        if duplicate is not None:
            return self._ok(
                {
                    "booking": self._booking_to_data(duplicate).model_dump(mode="json"),
                    "duplicate": True,
                    "message": "Matching active booking already exists",
                }
            )
        try:
            booking = self.booking_service.create_booking(
                customer_id=payload.customer_id,
                vehicle_id=payload.vehicle_id,
                service_id=payload.service_id,
                booking_date=payload.booking_date,
                booking_time=payload.booking_time,
                source=payload.source,
                notes=payload.notes,
            )
            return self._ok({"booking": self._booking_to_data(booking).model_dump(mode="json"), "duplicate": False})
        except Exception as exc:
            return self._map_exception(exc)

    def get_booking(self, payload: BookingLookupInput) -> AgentResult:
        try:
            booking = self.booking_service.get_booking(payload.booking_id)
            return self._ok({"booking": self._booking_to_data(booking).model_dump(mode="json")})
        except Exception as exc:
            return self._map_exception(exc)

    def reschedule_booking(self, payload: BookingRescheduleToolInput) -> AgentResult:
        try:
            booking = self.booking_service.reschedule_booking(
                payload.booking_id,
                new_date=payload.booking_date,
                new_time=payload.booking_time,
            )
            return self._ok({"booking": self._booking_to_data(booking).model_dump(mode="json")})
        except Exception as exc:
            return self._map_exception(exc)

    def cancel_booking(self, payload: BookingCancelToolInput) -> AgentResult:
        try:
            before = self.booking_service.get_booking(payload.booking_id)
            if before.status == BookingStatus.CANCELLED:
                return self._error(
                    error_code="BOOKING_ALREADY_CANCELLED",
                    message="Booking is already cancelled",
                    retryable=False,
                )
            cancelled = self.booking_service.cancel_booking(payload.booking_id)
            return self._ok(
                {
                    "booking_id": str(cancelled.id),
                    "previous_status": before.status.value,
                    "new_status": cancelled.status.value,
                }
            )
        except Exception as exc:
            return self._map_exception(exc)
