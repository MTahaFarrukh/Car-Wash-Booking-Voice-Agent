"""Pydantic schemas for API payloads and responses."""

from app.schemas.booking import AvailabilityCheckResult
from app.schemas.booking_api import AvailabilityQuery, BookingCreate, BookingResponse, BookingUpdate
from app.schemas.customer import CustomerCreate, CustomerResponse, CustomerUpdate
from app.schemas.service import ServiceResponse
from app.schemas.vehicle import VehicleCreate, VehicleResponse, VehicleUpdate

__all__ = [
    "AvailabilityCheckResult",
    "AvailabilityQuery",
    "BookingCreate",
    "BookingResponse",
    "BookingUpdate",
    "CustomerCreate",
    "CustomerResponse",
    "CustomerUpdate",
    "ServiceResponse",
    "VehicleCreate",
    "VehicleResponse",
    "VehicleUpdate",
]

