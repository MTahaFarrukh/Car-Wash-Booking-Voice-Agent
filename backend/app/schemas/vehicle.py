"""Vehicle API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class VehicleCreate(BaseModel):
    """Payload for creating a vehicle."""

    vehicle_type: str = Field(min_length=1, max_length=100)
    make: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=100)
    registration_number: str | None = Field(default=None, max_length=50)


class VehicleUpdate(BaseModel):
    """Payload for updating a vehicle."""

    vehicle_type: str | None = Field(default=None, min_length=1, max_length=100)
    make: str | None = Field(default=None, min_length=1, max_length=100)
    model: str | None = Field(default=None, min_length=1, max_length=100)
    registration_number: str | None = Field(default=None, max_length=50)


class VehicleResponse(BaseModel):
    """Vehicle response model."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    vehicle_type: str
    make: str
    model: str
    registration_number: str | None
    created_at: datetime
