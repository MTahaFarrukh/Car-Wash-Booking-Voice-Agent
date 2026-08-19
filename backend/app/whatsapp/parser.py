"""Natural-language parsing helpers for WhatsApp conversations."""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime, time, timedelta


WEEKDAY_NAMES = {
    "monday": 0,
    "mon": 0,
    "tuesday": 1,
    "tue": 1,
    "tues": 1,
    "wednesday": 2,
    "wed": 2,
    "thursday": 3,
    "thu": 3,
    "thur": 3,
    "thurs": 3,
    "friday": 4,
    "fri": 4,
    "saturday": 5,
    "sat": 5,
    "sunday": 6,
    "sun": 6,
}

AFFIRMATIONS = {"yes", "yeah", "yep", "sure", "confirm", "ok", "okay", "book it", "go ahead", "please do", "do it"}
NEGATIONS = {"no", "nope", "not now", "cancel that", "never mind", "nevermind", "don't", "do not"}

GREETING_KEYWORDS = {"hi", "hello", "hey", "salam", "assalam", "good morning", "good afternoon", "good evening"}
SERVICE_KEYWORDS = {"services", "service", "what do you offer", "what services", "wash options", "menu", "packages"}
BOOK_KEYWORDS = {"book", "booking", "schedule", "appointment", "reserve", "wash my car", "need a wash", "want a wash"}
CANCEL_KEYWORDS = {"cancel", "cancel my booking", "cancel booking", "call off"}
RESCHEDULE_KEYWORDS = {"reschedule", "move my booking", "change my booking", "move booking", "change time", "change date"}


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def is_greeting(text: str) -> bool:
    normalized = normalize_text(text)
    return normalized in GREETING_KEYWORDS or any(normalized.startswith(word) for word in ("hi ", "hello ", "hey "))


def is_affirmation(text: str) -> bool:
    normalized = normalize_text(text)
    if normalized in AFFIRMATIONS or normalized.startswith("yes "):
        return True
    if normalized.endswith(" yes") or normalized.endswith(". yes"):
        return True
    return normalized.rstrip(".!?") == "yes"


def is_negation(text: str) -> bool:
    normalized = normalize_text(text)
    return normalized in NEGATIONS


def detect_intent(text: str) -> str | None:
    normalized = normalize_text(text)
    if is_greeting(text):
        return "greeting"
    if any(keyword in normalized for keyword in CANCEL_KEYWORDS):
        return "cancel"
    if any(keyword in normalized for keyword in RESCHEDULE_KEYWORDS):
        return "reschedule"
    if any(keyword in normalized for keyword in SERVICE_KEYWORDS):
        return "list_services"
    if any(keyword in normalized for keyword in BOOK_KEYWORDS):
        return "book"
    if is_affirmation(text):
        return "confirm"
    if is_negation(text):
        return "deny"
    return None


def parse_date(text: str, *, today: date | None = None) -> date | None:
    reference = today or date.today()
    normalized = normalize_text(text)

    if "today" in normalized:
        return reference
    if "tomorrow" in normalized:
        return reference + timedelta(days=1)

    for name, weekday in WEEKDAY_NAMES.items():
        if re.search(rf"\b{re.escape(name)}\b", normalized):
            days_ahead = (weekday - reference.weekday()) % 7
            if days_ahead == 0 and "next" in normalized:
                days_ahead = 7
            elif days_ahead == 0 and name in normalized and "this" not in normalized:
                days_ahead = 7
            return reference + timedelta(days=days_ahead)

    iso_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", normalized)
    if iso_match:
        try:
            return date.fromisoformat(iso_match.group(1))
        except ValueError:
            return None

    slash_match = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b", normalized)
    if slash_match:
        day = int(slash_match.group(1))
        month = int(slash_match.group(2))
        year = slash_match.group(3)
        resolved_year = reference.year if year is None else int(year)
        if resolved_year < 100:
            resolved_year += 2000
        try:
            return date(resolved_year, month, day)
        except ValueError:
            return None

    return None


def parse_time(text: str) -> time | None:
    normalized = normalize_text(text)

    patterns = [
        r"\b(\d{1,2}):(\d{2})\s*(am|pm)?\b",
        r"\b(\d{1,2})\s*(am|pm)\b",
        r"\b(at\s+)?(\d{1,2}):(\d{2})\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, normalized)
        if not match:
            continue
        groups = [group for group in match.groups() if group and group != "at"]
        if len(groups) == 2 and groups[1] in {"am", "pm"}:
            hour = int(groups[0])
            minute = 0
            meridiem = groups[1]
        elif len(groups) == 3:
            hour = int(groups[0])
            minute = int(groups[1])
            meridiem = groups[2]
        elif len(groups) == 2 and groups[0].isdigit() and groups[1].isdigit():
            hour = int(groups[0])
            minute = int(groups[1])
            meridiem = None
        else:
            continue

        if meridiem == "pm" and hour < 12:
            hour += 12
        if meridiem == "am" and hour == 12:
            hour = 0
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return time(hour, minute)

    return None


def match_service(text: str, services: list[dict]) -> dict | None:
    normalized = normalize_text(text)
    best: dict | None = None
    best_score = 0

    for service in services:
        name = service["name"].lower()
        tokens = [token for token in re.split(r"[\s/+-]+", name) if token]
        score = 0
        if name in normalized:
            score += 5
        for token in tokens:
            if len(token) >= 4 and token in normalized:
                score += 2
        if "basic" in normalized and "basic" in name:
            score += 3
        if "premium" in normalized and "premium" in name:
            score += 3
        if "detail" in normalized and "detail" in name:
            score += 3
        if score > best_score:
            best = service
            best_score = score

    return best if best_score >= 2 else None


def match_vehicle(text: str, vehicles: list[dict]) -> dict | None:
    normalized = normalize_text(text)
    best: dict | None = None
    best_score = 0

    for vehicle in vehicles:
        make = vehicle.get("make", "").lower()
        model = vehicle.get("model", "").lower()
        label = f"{make} {model}".strip()
        score = 0
        if make and make in normalized:
            score += 2
        if model and model in normalized:
            score += 2
        if label and label in normalized:
            score += 4
        if "my car" in normalized or "my vehicle" in normalized:
            if len(vehicles) == 1:
                return vehicle
        if score > best_score:
            best = vehicle
            best_score = score

    return best if best_score >= 2 else None


def extract_entities(
    text: str,
    *,
    services: list[dict] | None = None,
    vehicles: list[dict] | None = None,
    today: date | None = None,
) -> dict:
    """Extract structured entities from free-form user text."""
    return {
        "service": match_service(text, services or []),
        "vehicle": match_vehicle(text, vehicles or []),
        "date": parse_date(text, today=today),
        "time": parse_time(text),
    }


def format_date(value: date) -> str:
    return value.strftime("%A, %B %d")


def format_time(value: time) -> str:
    suffix = "AM" if value.hour < 12 else "PM"
    hour = value.hour % 12 or 12
    if value.minute:
        return f"{hour}:{value.minute:02d} {suffix}"
    return f"{hour} {suffix}"


def format_booking_summary(
    *,
    service_name: str,
    booking_date: date,
    booking_time: time,
    vehicle_label: str | None = None,
) -> str:
    parts = [f"{service_name} on {format_date(booking_date)} at {format_time(booking_time)}"]
    if vehicle_label:
        parts.append(f"for your {vehicle_label}")
    return " ".join(parts)


def vehicle_label(vehicle: dict) -> str:
    make = vehicle.get("make", "")
    model = vehicle.get("model", "")
    return f"{make} {model}".strip()


def uuid_from_string(value: str) -> uuid.UUID:
    return uuid.UUID(str(value))
