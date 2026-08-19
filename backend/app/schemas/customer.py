"""Customer API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CustomerCreate(BaseModel):
    """Payload for creating a customer."""

    name: str = Field(min_length=1, max_length=255)
    phone: str = Field(min_length=3, max_length=32)
    email: str | None = None


class CustomerUpdate(BaseModel):
    """Payload for updating a customer."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, min_length=3, max_length=32)
    email: str | None = None


class CustomerResponse(BaseModel):
    """Customer response model."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    phone: str
    email: str | None
    created_at: datetime
    updated_at: datetime
