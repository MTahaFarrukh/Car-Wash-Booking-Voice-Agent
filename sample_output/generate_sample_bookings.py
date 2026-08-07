"""Generate sample bookings for assignment demonstration."""

import httpx

API_URL = "http://localhost:8000"

SAMPLE_BOOKINGS = [
    {
        "name": "Ali",
        "vehicle": "Civic",
        "date": "12 Aug",
        "time": "4 PM",
        "phone": "03001234567",
    },
    {
        "name": "Sara",
        "vehicle": "Corolla",
        "date": "15 Aug",
        "time": "10 AM",
        "phone": "03009876543",
    },
]


def main() -> None:
    print("Creating sample bookings...")
    for booking in SAMPLE_BOOKINGS:
        response = httpx.post(f"{API_URL}/booking", json=booking, timeout=10)
        print(f"  {booking['name']}: {response.status_code} -> {response.json()}")

    response = httpx.get(f"{API_URL}/bookings", timeout=10)
    print("\nAll bookings:")
    print(response.json())


if __name__ == "__main__":
    main()
