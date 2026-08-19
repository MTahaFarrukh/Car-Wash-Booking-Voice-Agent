"""Provider-independent schemas for AI agent tool inputs/outputs."""

from __future__ import annotations

import uuid
from datetime import date, time
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.booking import BookingSource, BookingStatus


ErrorCode = Literal[
    "CUSTOMER_NOT_FOUND",
    "VEHICLE_NOT_FOUND",
    "SERVICE_NOT_FOUND",
    "SLOT_UNAVAILABLE",
    "BOOKING_NOT_FOUND",
    "INVALID_BOOKING_TIME",
    "BOOKING_ALREADY_CANCELLED",
    "VALIDATION_ERROR",
    "DUPLICATE_REQUEST",
    "UNKNOWN_ERROR",
]


class AgentError(BaseModel):
    """Structured tool error for conversational handling."""

    error_code: ErrorCode
    message: str
    retryable: bool = False
    suggested_action: str | None = None


class AgentResult(BaseModel):
    """Generic tool execution result envelope."""

    success: bool
    data: dict[str, Any] | None = None
    error: AgentError | None = None


class CustomerToolInput(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    phone: str = Field(min_length=3, max_length=32)
    email: str | None = None


class CustomerLookupInput(BaseModel):
    customer_id: uuid.UUID | None = None
    phone: str | None = None


class VehicleCreateToolInput(BaseModel):
    customer_id: uuid.UUID
    vehicle_type: str = Field(min_length=1, max_length=100)
    make: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=100)
    registration_number: str | None = Field(default=None, max_length=50)


class VehicleLookupInput(BaseModel):
    customer_id: uuid.UUID | None = None
    vehicle_id: uuid.UUID | None = None


class ServicesListInput(BaseModel):
    active_only: bool = True


class AvailabilityToolInput(BaseModel):
    booking_date: date
    service_id: uuid.UUID
    requested_time: time | None = None


class BookingCreateToolInput(BaseModel):
    customer_id: uuid.UUID
    vehicle_id: uuid.UUID
    service_id: uuid.UUID
    booking_date: date
    booking_time: time
    source: BookingSource = BookingSource.VOICE
    notes: str | None = None
    idempotency_key: str | None = None


class BookingLookupInput(BaseModel):
    booking_id: uuid.UUID


class BookingRescheduleToolInput(BaseModel):
    booking_id: uuid.UUID
    booking_date: date
    booking_time: time


class BookingCancelToolInput(BaseModel):
    booking_id: uuid.UUID


class BookingData(BaseModel):
    booking_id: uuid.UUID
    customer_id: uuid.UUID
    vehicle_id: uuid.UUID
    service_id: uuid.UUID
    booking_date: date
    booking_time: time
    status: BookingStatus
    source: BookingSource
    notes: str | None = None
