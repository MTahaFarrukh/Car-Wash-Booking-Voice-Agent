"""Booking storage functions using CSV."""

import csv
from pathlib import Path

from config import BOOKINGS_CSV

CSV_HEADERS = ["Name", "Vehicle", "Date", "Time", "Phone"]


def _ensure_csv_exists() -> None:
    """Create bookings.csv with headers if it does not exist."""
    if not BOOKINGS_CSV.exists():
        with open(BOOKINGS_CSV, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(CSV_HEADERS)


def save_booking(name: str, vehicle: str, date: str, time: str, phone: str) -> dict:
    """
    Save a car wash booking to bookings.csv.

    Parameters: name, vehicle, date, time, phone
    Returns a dict with success status and saved booking data.
    """
    _ensure_csv_exists()

    booking = {
        "Name": name.strip(),
        "Vehicle": vehicle.strip(),
        "Date": date.strip(),
        "Time": time.strip(),
        "Phone": phone.strip(),
    }

    with open(BOOKINGS_CSV, "a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_HEADERS)
        writer.writerow(booking)

    return {"success": True, "message": "Booking saved successfully.", "booking": booking}


def get_all_bookings() -> list[dict]:
    """Read all bookings from the CSV file."""
    _ensure_csv_exists()

    with open(BOOKINGS_CSV, "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return list(reader)
