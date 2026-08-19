"""FastAPI application entry point."""

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import engine
from app.routers import (
    availability_router,
    bookings_router,
    customers_router,
    services_router,
    vehicles_router,
)

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


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok", "service": "Sparkle AI Receptionist API", "environment": settings.environment}


@app.get("/health/db")
def health_db() -> dict:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"database": "connected"}
    except SQLAlchemyError as exc:
        return {"database": "disconnected", "detail": str(exc)}
