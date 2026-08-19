"""Service catalog API routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.service import Service
from app.schemas.service import ServiceResponse

router = APIRouter(prefix="/api/services", tags=["services"])


@router.get("", response_model=list[ServiceResponse])
def list_services(
    active_only: bool = Query(default=True),
    db: Session = Depends(get_db),
) -> list[Service]:
    query = select(Service).order_by(Service.name.asc())
    if active_only:
        query = query.where(Service.active.is_(True))
    return list(db.scalars(query).all())


@router.get("/{service_id}", response_model=ServiceResponse)
def get_service(service_id: uuid.UUID, db: Session = Depends(get_db)) -> Service:
    service = db.get(Service, service_id)
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return service
