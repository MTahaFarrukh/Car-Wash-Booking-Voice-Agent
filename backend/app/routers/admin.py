"""Phase 9 admin read APIs — enriched bookings, CallLogs, WhatsApp activity, status."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.database import get_db
from app.models.booking import Booking, BookingSource, BookingStatus
from app.models.call_log import CallLog, CallOutcome
from app.models.customer import Customer
from app.models.whatsapp_message import WhatsAppProcessedMessage
from app.schemas.admin import (
    AdminStatusResponse,
    BookingListItem,
    CallLogResponse,
    ConnectionStatus,
    WhatsAppActivityItem,
)
from app.voice.provider import create_voice_provider

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _booking_list_item(booking: Booking) -> BookingListItem:
    vehicle_label = None
    if booking.vehicle is not None:
        vehicle_label = f"{booking.vehicle.make} {booking.vehicle.model}".strip()
    return BookingListItem(
        id=booking.id,
        customer_id=booking.customer_id,
        vehicle_id=booking.vehicle_id,
        service_id=booking.service_id,
        booking_date=booking.booking_date,
        booking_time=booking.booking_time,
        status=booking.status,
        source=booking.source,
        notes=booking.notes,
        created_at=booking.created_at,
        updated_at=booking.updated_at,
        customer_name=booking.customer.name if booking.customer else None,
        customer_phone=booking.customer.phone if booking.customer else None,
        vehicle_label=vehicle_label,
        service_name=booking.service.name if booking.service else None,
    )


@router.get("/bookings", response_model=list[BookingListItem])
def list_bookings_enriched(
    booking_date: date | None = Query(default=None),
    status_filter: BookingStatus | None = Query(default=None, alias="status"),
    source: BookingSource | None = Query(default=None),
    q: str | None = Query(default=None, description="Search customer name or phone"),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[BookingListItem]:
    stmt = (
        select(Booking)
        .options(
            joinedload(Booking.customer),
            joinedload(Booking.vehicle),
            joinedload(Booking.service),
        )
        .order_by(Booking.booking_date.desc(), Booking.booking_time.desc())
        .limit(limit)
    )
    if booking_date is not None:
        stmt = stmt.where(Booking.booking_date == booking_date)
    if status_filter is not None:
        stmt = stmt.where(Booking.status == status_filter)
    if source is not None:
        stmt = stmt.where(Booking.source == source)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.join(Booking.customer).where(
            (Customer.name.ilike(pattern)) | (Customer.phone.ilike(pattern))
        )
    rows = db.scalars(stmt).unique().all()
    return [_booking_list_item(row) for row in rows]


@router.get("/call-logs", response_model=list[CallLogResponse])
def list_call_logs(
    outcome: CallOutcome | None = Query(default=None),
    provider: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[CallLog]:
    stmt = select(CallLog).order_by(CallLog.started_at.desc()).limit(limit)
    if outcome is not None:
        stmt = stmt.where(CallLog.outcome == outcome)
    if provider:
        stmt = stmt.where(CallLog.provider == provider.strip().lower())
    return list(db.scalars(stmt).all())


@router.get("/whatsapp/activity", response_model=list[WhatsAppActivityItem])
def list_whatsapp_activity(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[WhatsAppProcessedMessage]:
    stmt = (
        select(WhatsAppProcessedMessage)
        .order_by(WhatsAppProcessedMessage.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


@router.get("/status", response_model=AdminStatusResponse)
def admin_status(db: Session = Depends(get_db)) -> AdminStatusResponse:
    settings = get_settings()
    db_ok = False
    db_detail: str | None = None
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
        db_detail = "connected"
    except SQLAlchemyError:
        db_detail = "unreachable"

    voice = create_voice_provider(settings)
    whatsapp_connected = bool((settings.whatsapp_bridge_secret or "").strip())
    llm_provider = (settings.llm_provider or "gemini").strip().lower()
    llm_ok = settings.llm_is_configured

    return AdminStatusResponse(
        database=ConnectionStatus(name="Database", connected=db_ok, detail=db_detail),
        gemini=ConnectionStatus(
            name="Gemini" if llm_provider == "gemini" else "LLM",
            connected=llm_ok,
            detail=llm_provider if llm_ok else "not configured",
        ),
        whatsapp=ConnectionStatus(
            name="WhatsApp",
            connected=whatsapp_connected,
            detail="bridge secret configured" if whatsapp_connected else "not configured",
        ),
        voice=ConnectionStatus(
            name="Voice Provider",
            connected=voice.is_configured(),
            detail=voice.name,
        ),
        environment=settings.environment,
    )
