"""Unit tests for pure slot generation logic."""

from datetime import time

from app.services.slot_engine import (
    OccupiedInterval,
    filter_available_slots,
    find_alternative_slots,
    generate_candidate_slots,
    is_slot_free,
    requested_time_is_valid,
)
from app.services.time_utils import intervals_overlap


OPENING = time(9, 0)
CLOSING = time(20, 0)
SLOT_STEP = 30


class TestGenerateCandidateSlots:
    def test_generates_slots_during_business_hours(self):
        slots = generate_candidate_slots(OPENING, CLOSING, SLOT_STEP, 30)
        assert time(9, 0) in slots
        assert time(19, 30) in slots
        assert all(slot >= OPENING for slot in slots)

    def test_no_slots_when_opening_equals_closing(self):
        slots = generate_candidate_slots(time(9, 0), time(9, 0), SLOT_STEP, 30)
        assert slots == []

    def test_service_duration_affects_last_slot(self):
        short_service_slots = generate_candidate_slots(OPENING, CLOSING, SLOT_STEP, 30)
        long_service_slots = generate_candidate_slots(OPENING, CLOSING, SLOT_STEP, 120)
        assert long_service_slots[-1] < short_service_slots[-1]
        assert time(19, 0) not in long_service_slots
        assert time(18, 0) in long_service_slots

    def test_two_hour_service_cannot_start_at_seven_pm_when_closing_at_eight(self):
        slots = generate_candidate_slots(OPENING, CLOSING, SLOT_STEP, 120)
        assert time(19, 0) not in slots


class TestConflictDetection:
    def test_existing_booking_blocks_overlap(self):
        occupied = [OccupiedInterval(start=time(16, 0), duration_minutes=60)]
        assert not is_slot_free(time(16, 30), 60, occupied)

    def test_back_to_back_booking_is_allowed(self):
        occupied = [OccupiedInterval(start=time(16, 0), duration_minutes=60)]
        assert is_slot_free(time(17, 0), 60, occupied)

    def test_cancelled_booking_not_in_occupied_list_does_not_block(self):
        occupied: list[OccupiedInterval] = []
        assert is_slot_free(time(16, 0), 60, occupied)

    def test_two_hour_booking_blocks_five_pm_start(self):
        occupied = [OccupiedInterval(start=time(16, 0), duration_minutes=120)]
        assert not is_slot_free(time(17, 0), 120, occupied)
        assert is_slot_free(time(18, 0), 120, occupied)

    def test_interval_overlap_helper(self):
        assert intervals_overlap(time(16, 0), 60, time(16, 30), 60)
        assert not intervals_overlap(time(16, 0), 60, time(17, 0), 60)


class TestBusinessHoursValidation:
    def test_requested_time_outside_hours_is_invalid(self):
        assert not requested_time_is_valid(time(8, 0), 60, OPENING, CLOSING)
        assert not requested_time_is_valid(time(19, 30), 120, OPENING, CLOSING)
        assert requested_time_is_valid(time(10, 0), 60, OPENING, CLOSING)


class TestAlternatives:
    def test_find_nearby_alternatives(self):
        available = [
            time(15, 0),
            time(16, 0),
            time(18, 0),
            time(19, 0),
        ]
        alternatives = find_alternative_slots(time(17, 0), available, limit=3)
        assert alternatives[0] in {time(16, 0), time(18, 0)}
        assert len(alternatives) <= 3


class TestInactiveDay:
    def test_no_slots_without_schedule(self):
        slots = filter_available_slots([], 30, [])
        assert slots == []
