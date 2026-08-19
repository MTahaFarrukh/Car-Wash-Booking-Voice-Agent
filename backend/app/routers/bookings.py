"""Booking API routes."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.exceptions import AppError
from app.models.booking import Booking, BookingSource, BookingStatus
from app.schemas.booking_api import BookingCreate, BookingResponse, BookingUpdate
from app.services.booking_service import BookingService
from app.routers.utils import raise_http_for_domain_error

router = APIRouter(tags=["bookings"])


@router.post("/api/bookings", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(payload: BookingCreate, db: Session = Depends(get_db)) -> Booking:
    service = BookingService(db)
    try:
        return service.create_booking(**payload.model_dump())
    except AppError as exc:
        raise_http_for_domain_error(exc)


@router.get("/api/bookings/{booking_id}", response_model=BookingResponse)
def get_booking(booking_id: uuid.UUID, db: Session = Depends(get_db)) -> Booking:
    service = BookingService(db)
    try:
        return service.get_booking(booking_id)
    except AppError as exc:
        raise_http_for_domain_error(exc)


@router.get("/api/bookings", response_model=list[BookingResponse])
def list_bookings(
    booking_date: date | None = Query(default=None),
    status_filter: BookingStatus | None = Query(default=None, alias="status"),
    customer_id: uuid.UUID | None = Query(default=None),
    source: BookingSource | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[Booking]:
    service = BookingService(db)
    return service.get_bookings(
        booking_date=booking_date,
        status=status_filter,
        customer_id=customer_id,
        source=source,
    )


@router.patch("/api/bookings/{booking_id}", response_model=BookingResponse)
def update_booking(
    booking_id: uuid.UUID,
    payload: BookingUpdate,
    db: Session = Depends(get_db),
) -> Booking:
    service = BookingService(db)
    try:
        if payload.status == BookingStatus.CANCELLED:
            return service.cancel_booking(booking_id)

        if payload.booking_date is not None and payload.booking_time is not None:
            updated = service.reschedule_booking(
                booking_id,
                new_date=payload.booking_date,
                new_time=payload.booking_time,
            )
            if payload.notes is not None:
                updated.notes = payload.notes
                db.commit()
                db.refresh(updated)
            return updated

        if payload.notes is not None:
            booking = service.get_booking(booking_id)
            booking.notes = payload.notes
            db.commit()
            db.refresh(booking)
            return booking

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only cancel, reschedule, or notes update is supported",
        )
    except AppError as exc:
        raise_http_for_domain_error(exc)


@router.delete("/api/bookings/{booking_id}", response_model=BookingResponse)
def cancel_booking(booking_id: uuid.UUID, db: Session = Depends(get_db)) -> Booking:
    service = BookingService(db)
    try:
        return service.cancel_booking(booking_id)
    except AppError as exc:
        raise_http_for_domain_error(exc)


@router.get("/api/customers/{customer_id}/bookings", response_model=list[BookingResponse])
def list_customer_bookings(customer_id: uuid.UUID, db: Session = Depends(get_db)) -> list[Booking]:
    service = BookingService(db)
    try:
        return service.get_customer_bookings(customer_id)
    except AppError as exc:
        raise_http_for_domain_error(exc)
