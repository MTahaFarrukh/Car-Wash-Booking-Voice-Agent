"""Phase 9 admin read APIs — enriched bookings, CallLogs, WhatsApp activity, status."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.auth.deps import require_admin
from app.core.config import get_settings
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.models.booking import Booking, BookingSource, BookingStatus
from app.models.call_log import CallLog, CallOutcome
from app.models.customer import Customer
from app.models.whatsapp_message import WhatsAppProcessedMessage
from app.schemas.admin import (
    AcknowledgeBookingResponse,
    AdminNotificationCount,
    AdminStatusResponse,
    BookingListItem,
    CallLogResponse,
    ConnectionStatus,
    WhatsAppActivityItem,
)
from app.voice.provider import create_voice_provider

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


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
        admin_acknowledged_at=booking.admin_acknowledged_at,
        created_at=booking.created_at,
        updated_at=booking.updated_at,
        customer_name=booking.customer.name if booking.customer else None,
        customer_phone=booking.customer.phone if booking.customer else None,
        vehicle_label=vehicle_label,
        service_name=booking.service.name if booking.service else None,
    )


@router.get("/me")
def admin_me(admin: AdminUser = Depends(require_admin)) -> dict:
    """Return the authenticated admin profile (for dashboard chrome)."""
    return {
        "id": str(admin.id),
        "email": admin.email,
        "role": admin.role,
        "auth_user_id": str(admin.auth_user_id),
    }


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
        # Newest creations first so recent ops bookings aren't buried under far-future seed rows.
        .order_by(
            Booking.created_at.desc(),
            Booking.booking_date.desc(),
            Booking.booking_time.desc(),
        )
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


def _unacknowledged_stmt(limit: int | None = None):
    stmt = (
        select(Booking)
        .options(
            joinedload(Booking.customer),
            joinedload(Booking.vehicle),
            joinedload(Booking.service),
        )
        .where(
            Booking.admin_acknowledged_at.is_(None),
            Booking.status != BookingStatus.CANCELLED,
        )
        .order_by(Booking.created_at.desc())
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    return stmt


@router.get("/notifications/count", response_model=AdminNotificationCount)
def unacknowledged_notification_count(db: Session = Depends(get_db)) -> AdminNotificationCount:
    count = db.scalar(
        select(func.count())
        .select_from(Booking)
        .where(
            Booking.admin_acknowledged_at.is_(None),
            Booking.status != BookingStatus.CANCELLED,
        )
    )
    return AdminNotificationCount(count=int(count or 0))


@router.get("/notifications", response_model=list[BookingListItem])
def list_unacknowledged_notifications(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[BookingListItem]:
    rows = db.scalars(_unacknowledged_stmt(limit)).unique().all()
    return [_booking_list_item(row) for row in rows]


@router.post("/bookings/{booking_id}/acknowledge", response_model=AcknowledgeBookingResponse)
def acknowledge_booking(
    booking_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> AcknowledgeBookingResponse:
    booking = db.scalar(
        select(Booking)
        .options(joinedload(Booking.customer), joinedload(Booking.vehicle), joinedload(Booking.service))
        .where(Booking.id == booking_id)
    )
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    if booking.status == BookingStatus.CANCELLED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cancelled booking cannot be accepted")
    if booking.admin_acknowledged_at is not None:
        return AcknowledgeBookingResponse(
            id=booking.id,
            status=booking.status,
            admin_acknowledged_at=booking.admin_acknowledged_at,
        )

    now = datetime.now(timezone.utc)
    booking.admin_acknowledged_at = now
    if booking.status == BookingStatus.PENDING:
        booking.status = BookingStatus.CONFIRMED
    db.commit()
    db.refresh(booking)
    return AcknowledgeBookingResponse(
        id=booking.id,
        status=booking.status,
        admin_acknowledged_at=booking.admin_acknowledged_at,
    )


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
