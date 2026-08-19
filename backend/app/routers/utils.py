"""Shared router utilities."""

from fastapi import HTTPException, status

from app.exceptions import (
    BookingNotFoundError,
    BusinessClosedError,
    CustomerNotFoundError,
    InvalidBookingError,
    ServiceNotFoundError,
    SlotUnavailableError,
    VehicleNotFoundError,
)


def raise_http_for_domain_error(exc: Exception) -> None:
    """Map domain/service exceptions to HTTP errors."""
    if isinstance(exc, (CustomerNotFoundError, VehicleNotFoundError, ServiceNotFoundError, BookingNotFoundError)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, (SlotUnavailableError, BusinessClosedError)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, InvalidBookingError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise exc
