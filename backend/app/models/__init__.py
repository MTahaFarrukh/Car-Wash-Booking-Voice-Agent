"""SQLAlchemy models for the car wash booking platform."""

from app.models.availability import Availability
from app.models.booking import Booking, BookingSource, BookingStatus
from app.models.call_log import CallLog, CallOutcome
from app.models.customer import Customer
from app.models.service import Service
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.whatsapp_message import WhatsAppProcessedMessage

__all__ = [
    "Availability",
    "Booking",
    "BookingSource",
    "BookingStatus",
    "CallLog",
    "CallOutcome",
    "Customer",
    "Service",
    "User",
    "Vehicle",
    "WhatsAppProcessedMessage",
]
