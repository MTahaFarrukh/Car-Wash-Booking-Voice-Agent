"""Booking API request/response schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.booking import BookingSource, BookingStatus


class BookingCreate(BaseModel):
    """Payload for creating a booking."""

    customer_id: uuid.UUID
    vehicle_id: uuid.UUID
    service_id: uuid.UUID
    booking_date: date
    booking_time: time
    source: BookingSource = BookingSource.DASHBOARD
    notes: str | None = None


class BookingUpdate(BaseModel):
    """Payload for updating or cancelling a booking."""

    booking_date: date | None = None
    booking_time: time | None = None
    status: BookingStatus | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_fields(self) -> "BookingUpdate":
        if self.booking_date is None and self.booking_time is None and self.status is None and self.notes is None:
            raise ValueError("At least one field must be provided")
        if (self.booking_date is None) != (self.booking_time is None):
            raise ValueError("booking_date and booking_time must be provided together")
        return self


class BookingResponse(BaseModel):
    """Booking response model."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    vehicle_id: uuid.UUID
    service_id: uuid.UUID
    booking_date: date
    booking_time: time
    status: BookingStatus
    source: BookingSource
    notes: str | None
    created_at: datetime
    updated_at: datetime


class AvailabilityQuery(BaseModel):
    """Availability endpoint query model."""

    booking_date: date
    service_id: uuid.UUID
    requested_time: time | None = Field(default=None)
