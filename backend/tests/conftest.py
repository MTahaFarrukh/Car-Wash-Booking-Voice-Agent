"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import os
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

os.environ.setdefault("WHATSAPP_BRIDGE_SECRET", "test-bridge-secret")

from app.core.config import get_settings

get_settings.cache_clear()
settings = get_settings()


def database_is_available() -> bool:
    """Return True when PostgreSQL is reachable."""
    try:
        engine = create_engine(settings.database_url, pool_pre_ping=True)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


DB_AVAILABLE = database_is_available()

requires_database = pytest.mark.skipif(
    not DB_AVAILABLE,
    reason="PostgreSQL is not available — set DATABASE_URL and start the database",
)


@pytest.fixture(scope="session")
def db_engine():
    if not DB_AVAILABLE:
        pytest.skip("PostgreSQL is not available")
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine) -> Generator[Session, None, None]:
    session_factory = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
