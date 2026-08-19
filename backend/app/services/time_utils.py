"""Pure date/time helpers for booking logic."""

from datetime import date, datetime, time, timedelta


def time_to_minutes(value: time) -> int:
    """Convert a time to minutes since midnight."""
    return value.hour * 60 + value.minute


def minutes_to_time(total_minutes: int) -> time:
    """Convert minutes since midnight to a time."""
    hours, minutes = divmod(total_minutes, 60)
    return time(hour=hours, minute=minutes)


def add_minutes_to_time(value: time, minutes: int) -> time:
    """Add minutes to a time, wrapping within the same day."""
    return minutes_to_time(time_to_minutes(value) + minutes)


def combine_date_time(booking_date: date, booking_time: time) -> datetime:
    """Combine a date and time into a naive datetime."""
    return datetime.combine(booking_date, booking_time)


def is_past_slot(booking_date: date, booking_time: time, now: datetime | None = None) -> bool:
    """Return True when the slot is in the past relative to now."""
    current = now or datetime.now()
    return combine_date_time(booking_date, booking_time) < current.replace(tzinfo=None)


def intervals_overlap(
    start_a: time,
    duration_a_minutes: int,
    start_b: time,
    duration_b_minutes: int,
) -> bool:
    """Return True when two [start, start+duration) intervals overlap.

    Back-to-back appointments do not overlap. For example, 16:00-17:00 and 17:00-18:00
    are allowed.
    """
    a_start = time_to_minutes(start_a)
    a_end = a_start + duration_a_minutes
    b_start = time_to_minutes(start_b)
    b_end = b_start + duration_b_minutes
    return a_start < b_end and b_start < a_end


def slot_fits_before_closing(
    slot_start: time,
    service_duration_minutes: int,
    closing_time: time,
) -> bool:
    """Return True when the full service fits before closing time."""
    return time_to_minutes(slot_start) + service_duration_minutes <= time_to_minutes(closing_time)


def is_within_business_hours(
    slot_start: time,
    service_duration_minutes: int,
    opening_time: time,
    closing_time: time,
) -> bool:
    """Return True when a slot starts within hours and ends by closing."""
    start_minutes = time_to_minutes(slot_start)
    opening_minutes = time_to_minutes(opening_time)
    closing_minutes = time_to_minutes(closing_time)
    return opening_minutes <= start_minutes and start_minutes + service_duration_minutes <= closing_minutes


def distance_between_times(left: time, right: time) -> int:
    """Absolute difference in minutes between two times."""
    return abs(time_to_minutes(left) - time_to_minutes(right))


def date_weekday(booking_date: date) -> int:
    """Return day of week using Monday=0 .. Sunday=6."""
    return booking_date.weekday()
