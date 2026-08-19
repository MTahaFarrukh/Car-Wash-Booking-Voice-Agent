"""Availability API routes."""

from __future__ import annotations

import uuid
from datetime import date, time

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.booking import AvailabilityCheckResult
from app.services.availability_service import AvailabilityService

router = APIRouter(prefix="/api/availability", tags=["availability"])


@router.get("", response_model=AvailabilityCheckResult)
def check_availability(
    booking_date: date = Query(...),
    service_id: uuid.UUID = Query(...),
    requested_time: time | None = Query(default=None),
    db: Session = Depends(get_db),
) -> AvailabilityCheckResult:
    service = AvailabilityService(db)
    return service.check_availability(
        booking_date=booking_date,
        service_id=service_id,
        requested_time=requested_time,
    )
