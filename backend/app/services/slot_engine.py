"""Pure slot generation and conflict detection logic."""

from dataclasses import dataclass
from datetime import time

from app.models.booking import BookingStatus
from app.services.time_utils import (
    intervals_overlap,
    is_within_business_hours,
    minutes_to_time,
    slot_fits_before_closing,
    time_to_minutes,
)

# Only active bookings block availability.
BLOCKING_STATUSES: frozenset[BookingStatus] = frozenset(
    {BookingStatus.PENDING, BookingStatus.CONFIRMED}
)


@dataclass(frozen=True)
class OccupiedInterval:
    """A time interval occupied by an existing booking."""

    start: time
    duration_minutes: int


def generate_candidate_slots(
    opening_time: time,
    closing_time: time,
    slot_duration_minutes: int,
    service_duration_minutes: int,
) -> list[time]:
    """Generate all candidate start times that fit within business hours."""
    if slot_duration_minutes <= 0 or service_duration_minutes <= 0:
        return []

    slots: list[time] = []
    cursor = time_to_minutes(opening_time)
    closing = time_to_minutes(closing_time)

    while cursor + service_duration_minutes <= closing:
        slot = minutes_to_time(cursor)
        if slot_fits_before_closing(slot, service_duration_minutes, closing_time):
            slots.append(slot)
        cursor += slot_duration_minutes

    return slots


def is_slot_free(
    slot_start: time,
    service_duration_minutes: int,
    occupied_intervals: list[OccupiedInterval],
) -> bool:
    """Return True when the slot does not overlap any occupied interval."""
    return all(
        not intervals_overlap(slot_start, service_duration_minutes, occupied.start, occupied.duration_minutes)
        for occupied in occupied_intervals
    )


def filter_available_slots(
    candidate_slots: list[time],
    service_duration_minutes: int,
    occupied_intervals: list[OccupiedInterval],
) -> list[time]:
    """Filter candidate slots to those without conflicts."""
    return [
        slot
        for slot in candidate_slots
        if is_slot_free(slot, service_duration_minutes, occupied_intervals)
    ]


def requested_time_is_valid(
    requested_time: time,
    service_duration_minutes: int,
    opening_time: time,
    closing_time: time,
) -> bool:
    """Return True when the requested time is inside business hours."""
    return is_within_business_hours(requested_time, service_duration_minutes, opening_time, closing_time)


def find_alternative_slots(
    requested_time: time,
    available_slots: list[time],
    *,
    limit: int = 5,
) -> list[time]:
    """Return nearby alternative slots sorted by proximity to the requested time."""
    alternatives = [slot for slot in available_slots if slot != requested_time]
    alternatives.sort(key=lambda slot: abs(time_to_minutes(slot) - time_to_minutes(requested_time)))
    return alternatives[:limit]
