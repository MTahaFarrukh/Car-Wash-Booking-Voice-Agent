"""FastAPI application entry point."""

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core.database import engine
from app.routers import (
    admin_router,
    availability_router,
    bookings_router,
    customers_router,
    services_router,
    vehicles_router,
    voice_router,
    whatsapp_router,
)
from app.routers.voice import vapi_alias_router

# Import models so SQLAlchemy registers metadata (used by Alembic in Phase 2)
import app.models  # noqa: F401

settings = get_settings()

app = FastAPI(
    title="Sparkle AI Receptionist API",
    description="Backend API for the AI car wash receptionist and booking platform.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(customers_router)
app.include_router(vehicles_router)
app.include_router(services_router)
app.include_router(availability_router)
app.include_router(bookings_router)
app.include_router(whatsapp_router)
app.include_router(voice_router)
app.include_router(vapi_alias_router)
app.include_router(admin_router)


@app.get("/health")
def health_check() -> dict:
    """Liveness probe — process is up (no secrets)."""
    return {
        "status": "ok",
        "service": "Sparkle AI Receptionist API",
        "environment": settings.environment,
    }


@app.get("/health/db")
def health_db(response: Response) -> dict:
    """Readiness probe — database connectivity (503 when unreachable)."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except SQLAlchemyError as exc:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "error",
            "database": "disconnected",
            "detail": type(exc).__name__,
        }
