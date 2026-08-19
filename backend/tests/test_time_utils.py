"""Unit tests for date/time helpers."""

from datetime import date, datetime, time

from app.services.time_utils import is_past_slot


class TestPastBookings:
    def test_past_slot_is_rejected(self):
        assert is_past_slot(
            date(2020, 1, 1),
            time(16, 0),
            now=datetime(2026, 1, 1, 18, 0),
        )

    def test_future_slot_is_allowed(self):
        assert not is_past_slot(
            date(2030, 1, 1),
            time(10, 0),
            now=datetime(2026, 1, 1, 18, 0),
        )

    def test_today_future_time_is_allowed(self):
        now = datetime(2026, 8, 19, 10, 0)
        assert not is_past_slot(date(2026, 8, 19), time(15, 0), now=now)

    def test_today_past_time_is_rejected(self):
        now = datetime(2026, 8, 19, 18, 0)
        assert is_past_slot(date(2026, 8, 19), time(16, 0), now=now)
