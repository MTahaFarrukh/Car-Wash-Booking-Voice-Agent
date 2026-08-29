"""Admin / ops read-only schemas (Phase 9). No secrets in responses."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict

from app.models.booking import BookingSource, BookingStatus
from app.models.call_log import CallOutcome


class CallLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    call_id: str
    provider: str | None
    customer_id: uuid.UUID | None
    phone: str | None
    started_at: datetime
    duration_seconds: int | None
    outcome: CallOutcome
    booking_id: uuid.UUID | None


class WhatsAppActivityItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    message_id: str
    sender_id: str
    response_message: str
    created_at: datetime


class ConnectionStatus(BaseModel):
    name: str
    connected: bool
    detail: str | None = None


class AdminStatusResponse(BaseModel):
    database: ConnectionStatus
    gemini: ConnectionStatus
    whatsapp: ConnectionStatus
    voice: ConnectionStatus
    environment: str


class BookingListItem(BaseModel):
    """Booking row with joined labels for admin tables."""

    id: uuid.UUID
    customer_id: uuid.UUID
    vehicle_id: uuid.UUID
    service_id: uuid.UUID
    booking_date: date
    booking_time: time
    status: BookingStatus
    source: BookingSource
    notes: str | None
    admin_acknowledged_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    customer_name: str | None = None
    customer_phone: str | None = None
    vehicle_label: str | None = None
    service_name: str | None = None


class AdminNotificationCount(BaseModel):
    count: int


class AcknowledgeBookingResponse(BaseModel):
    id: uuid.UUID
    status: BookingStatus
    admin_acknowledged_at: datetime
