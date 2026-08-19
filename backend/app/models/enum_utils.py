"""Shared SQLAlchemy enum helpers."""

from enum import Enum


def enum_values(enum_class: type[Enum]) -> list[str]:
    """Return enum values for PostgreSQL (lowercase), not member names."""
    return [member.value for member in enum_class]
