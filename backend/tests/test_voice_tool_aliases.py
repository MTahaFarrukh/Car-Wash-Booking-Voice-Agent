"""Unit tests for voice tool aliases (service matching + save_booking helpers)."""

from __future__ import annotations

import uuid

from app.voice.state import CallSessionState
from app.voice.tool_aliases import _match_service_row, _resolve_service, normalize_tool_name


def _rows() -> list[dict]:
    return [
        {"service_id": str(uuid.uuid4()), "name": "Basic Wash"},
        {"service_id": str(uuid.uuid4()), "name": "Premium Wash"},
        {"service_id": str(uuid.uuid4()), "name": "Full Detailing"},
    ]


class TestNormalizeToolName:
    def test_save_booking_aliases(self):
        assert normalize_tool_name("Save Booking") == "save_booking"
        assert normalize_tool_name("save_booking") == "save_booking"
        assert normalize_tool_name("book-appointment") == "save_booking"


class TestMatchServiceRow:
    def test_exact_and_substring(self):
        rows = _rows()
        assert _match_service_row(rows, "Basic Wash")["name"] == "Basic Wash"
        assert _match_service_row(rows, "basic")["name"] == "Basic Wash"
        assert _match_service_row(rows, "premium wash")["name"] == "Premium Wash"

    def test_detailing_synonym_without_premium_default(self):
        rows = _rows()
        assert _match_service_row(rows, "Interior Detailing")["name"] == "Full Detailing"
        assert _match_service_row(rows, "") is None
        assert _match_service_row(rows, "unknown package") is None


class TestResolveService:
    def test_defaults_to_first_catalog_service_when_missing(self):
        rows = _rows()
        state = CallSessionState(call_id="c1")
        matched, err = _resolve_service(rows, {}, state)
        assert err is None
        assert matched is not None
        assert matched["name"] == "Basic Wash"

    def test_uses_session_selection(self):
        rows = _rows()
        state = CallSessionState(
            call_id="c2",
            selected_service_id=uuid.UUID(rows[0]["service_id"]),
            selected_service_name="Basic Wash",
        )
        matched, err = _resolve_service(rows, {}, state)
        assert err is None
        assert matched is not None
        assert matched["name"] == "Basic Wash"

    def test_explicit_arg_overrides_defaulting(self):
        rows = _rows()
        state = CallSessionState(call_id="c3")
        matched, err = _resolve_service(rows, {"service": "Full Detailing"}, state)
        assert err is None
        assert matched["name"] == "Full Detailing"
