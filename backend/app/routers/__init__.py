"""API router package."""

from app.routers.availability import router as availability_router
from app.routers.bookings import router as bookings_router
from app.routers.customers import router as customers_router
from app.routers.services import router as services_router
from app.routers.vehicles import router as vehicles_router
from app.routers.whatsapp import router as whatsapp_router

__all__ = [
    "availability_router",
    "bookings_router",
    "customers_router",
    "services_router",
    "vehicles_router",
    "whatsapp_router",
]

