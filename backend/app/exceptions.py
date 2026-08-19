"""Application-level domain exceptions."""


class AppError(Exception):
    """Base application error."""


class BookingNotFoundError(AppError):
    """Raised when a booking cannot be found."""


class SlotUnavailableError(AppError):
    """Raised when a requested booking slot is not available."""


class InvalidBookingError(AppError):
    """Raised when booking input or state is invalid."""


class CustomerNotFoundError(AppError):
    """Raised when a customer cannot be found."""


class VehicleNotFoundError(AppError):
    """Raised when a vehicle cannot be found."""


class ServiceNotFoundError(AppError):
    """Raised when a service cannot be found."""


class BusinessClosedError(AppError):
    """Raised when the business is closed on the requested date."""
