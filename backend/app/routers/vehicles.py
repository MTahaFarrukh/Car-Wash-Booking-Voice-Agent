"""Vehicle API routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models.customer import Customer
from app.models.vehicle import Vehicle
from app.schemas.vehicle import VehicleCreate, VehicleResponse, VehicleUpdate

router = APIRouter(tags=["vehicles"])


@router.get("/api/vehicles", response_model=list[VehicleResponse])
def list_vehicles(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[Vehicle]:
    stmt = (
        select(Vehicle)
        .options(joinedload(Vehicle.customer))
        .order_by(Vehicle.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt).unique().all())


@router.post(
    "/api/customers/{customer_id}/vehicles",
    response_model=VehicleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_vehicle_for_customer(
    customer_id: uuid.UUID,
    payload: VehicleCreate,
    db: Session = Depends(get_db),
) -> Vehicle:
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    vehicle = Vehicle(customer_id=customer_id, **payload.model_dump())
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.get("/api/customers/{customer_id}/vehicles", response_model=list[VehicleResponse])
def list_customer_vehicles(customer_id: uuid.UUID, db: Session = Depends(get_db)) -> list[Vehicle]:
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    return list(
        db.scalars(select(Vehicle).where(Vehicle.customer_id == customer_id).order_by(Vehicle.created_at.desc())).all()
    )


@router.get("/api/vehicles/{vehicle_id}", response_model=VehicleResponse)
def get_vehicle(vehicle_id: uuid.UUID, db: Session = Depends(get_db)) -> Vehicle:
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    return vehicle


@router.patch("/api/vehicles/{vehicle_id}", response_model=VehicleResponse)
def update_vehicle(
    vehicle_id: uuid.UUID,
    payload: VehicleUpdate,
    db: Session = Depends(get_db),
) -> Vehicle:
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(vehicle, field, value)

    db.commit()
    db.refresh(vehicle)
    return vehicle
