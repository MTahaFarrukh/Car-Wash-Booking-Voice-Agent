"""Service catalog domain operations."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import ServiceNotFoundError
from app.models.service import Service


class ServiceCatalogService:
    """Read-only service catalog operations."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_services(self, *, active_only: bool = True) -> list[Service]:
        query = select(Service).order_by(Service.name.asc())
        if active_only:
            query = query.where(Service.active.is_(True))
        return list(self.db.scalars(query).all())

    def get_service(self, service_id: uuid.UUID) -> Service:
        service = self.db.get(Service, service_id)
        if service is None:
            raise ServiceNotFoundError(f"Service {service_id} not found")
        return service
