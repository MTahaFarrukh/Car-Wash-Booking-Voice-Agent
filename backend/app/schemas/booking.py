"""Pydantic schemas for booking domain results."""

from datetime import time

from pydantic import BaseModel, Field


class AvailabilityCheckResult(BaseModel):
    """Structured availability check response."""

    available: bool
    requested_time: time | None = None
    alternatives: list[time] = Field(default_factory=list)
    message: str | None = None
