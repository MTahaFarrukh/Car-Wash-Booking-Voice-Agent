"""Idempotent development seed data for Sparkle Car Wash.

Run from the backend directory:

    python -m scripts.seed
"""

from __future__ import annotations

import sys
import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import (
    Availability,
    Booking,
    BookingSource,
    BookingStatus,
    CallLog,
    CallOutcome,
    Customer,
    Service,
    User,
    Vehicle,
)

SEED_ADMIN_EMAIL = "admin@sparklecarwash.test"
SEED_MARKER_PHONE = "+92-300-0000001"

SERVICES = [
    {
        "name": "Basic Wash",
        "description": "Exterior hand wash, tire shine, and window cleaning.",
        "price": Decimal("800.00"),
        "duration_minutes": 30,
    },
    {
        "name": "Premium Wash",
        "description": "Exterior wash, interior vacuum, dashboard wipe, and wax finish.",
        "price": Decimal("1500.00"),
        "duration_minutes": 60,
    },
    {
        "name": "Full Detailing",
        "description": "Complete interior and exterior detailing with polish and protection.",
        "price": Decimal("3500.00"),
        "duration_minutes": 120,
    },
]

CUSTOMERS = [
    {"name": "Ahmed Khan", "phone": "+92-300-0000001", "email": "ahmed.khan@test.sparkle"},
    {"name": "Bilal Ahmed", "phone": "+92-300-0000002", "email": "bilal.ahmed@test.sparkle"},
    {"name": "Hamza Siddiqui", "phone": "+92-300-0000003", "email": "hamza.siddiqui@test.sparkle"},
    {"name": "Usman Tariq", "phone": "+92-300-0000004", "email": "usman.tariq@test.sparkle"},
    {"name": "Ali Raza", "phone": "+92-300-0000005", "email": "ali.raza@test.sparkle"},
    {"name": "Hassan Malik", "phone": "+92-300-0000006", "email": "hassan.malik@test.sparkle"},
    {"name": "Omar Farooq", "phone": "+92-300-0000007", "email": "omar.farooq@test.sparkle"},
    {"name": "Saad Iqbal", "phone": "+92-300-0000008", "email": "saad.iqbal@test.sparkle"},
]

VEHICLES = [
    {"make": "Honda", "model": "Civic", "vehicle_type": "sedan", "registration_number": "TEST-001"},
    {"make": "Toyota", "model": "Corolla", "vehicle_type": "sedan", "registration_number": "TEST-002"},
    {"make": "Toyota", "model": "Yaris", "vehicle_type": "hatchback", "registration_number": "TEST-003"},
    {"make": "Suzuki", "model": "Alto", "vehicle_type": "hatchback", "registration_number": "TEST-004"},
    {"make": "Kia", "model": "Sportage", "vehicle_type": "suv", "registration_number": "TEST-005"},
    {"make": "Hyundai", "model": "Tucson", "vehicle_type": "suv", "registration_number": "TEST-006"},
    {"make": "Toyota", "model": "Fortuner", "vehicle_type": "suv", "registration_number": "TEST-007"},
]

AVAILABILITY = [
    {"day_of_week": 0, "opening_time": time(9, 0), "closing_time": time(20, 0)},
    {"day_of_week": 1, "opening_time": time(9, 0), "closing_time": time(20, 0)},
    {"day_of_week": 2, "opening_time": time(9, 0), "closing_time": time(20, 0)},
    {"day_of_week": 3, "opening_time": time(9, 0), "closing_time": time(20, 0)},
    {"day_of_week": 4, "opening_time": time(9, 0), "closing_time": time(20, 0)},
    {"day_of_week": 5, "opening_time": time(10, 0), "closing_time": time(20, 0)},
    {"day_of_week": 6, "opening_time": time(10, 0), "closing_time": time(18, 0)},
]


def is_seeded(session) -> bool:
    """Return True when development seed data is already present."""
    admin = session.scalar(select(User).where(User.email == SEED_ADMIN_EMAIL))
    marker_customer = session.scalar(select(Customer).where(Customer.phone == SEED_MARKER_PHONE))
    return admin is not None and marker_customer is not None


def seed_admin(session) -> User:
    admin = session.scalar(select(User).where(User.email == SEED_ADMIN_EMAIL))
    if admin:
        return admin

    admin = User(email=SEED_ADMIN_EMAIL, name="Sparkle Admin")
    session.add(admin)
    session.flush()
    return admin


def seed_services(session) -> dict[str, Service]:
    services: dict[str, Service] = {}
    for item in SERVICES:
        existing = session.scalar(select(Service).where(Service.name == item["name"]))
        if existing:
            services[item["name"]] = existing
            continue

        service = Service(
            name=item["name"],
            description=item["description"],
            price=item["price"],
            duration_minutes=item["duration_minutes"],
            active=True,
        )
        session.add(service)
        session.flush()
        services[item["name"]] = service
    return services


def seed_customers(session) -> list[Customer]:
    customers: list[Customer] = []
    for item in CUSTOMERS:
        existing = session.scalar(select(Customer).where(Customer.phone == item["phone"]))
        if existing:
            customers.append(existing)
            continue

        customer = Customer(name=item["name"], phone=item["phone"], email=item["email"])
        session.add(customer)
        session.flush()
        customers.append(customer)
    return customers


def seed_vehicles(session, customers: list[Customer]) -> list[Vehicle]:
    vehicles: list[Vehicle] = []
    for index, customer in enumerate(customers):
        spec = VEHICLES[index % len(VEHICLES)]
        registration_number = f"TEST-{index + 1:03d}"
        existing = session.scalar(
            select(Vehicle).where(
                Vehicle.customer_id == customer.id,
                Vehicle.registration_number == registration_number,
            )
        )
        if existing:
            vehicles.append(existing)
            continue

        vehicle = Vehicle(
            customer_id=customer.id,
            make=spec["make"],
            model=spec["model"],
            vehicle_type=spec["vehicle_type"],
            registration_number=registration_number,
        )
        session.add(vehicle)
        session.flush()
        vehicles.append(vehicle)
    return vehicles


def seed_availability(session) -> list[Availability]:
    rows: list[Availability] = []
    for item in AVAILABILITY:
        existing = session.scalar(
            select(Availability).where(Availability.day_of_week == item["day_of_week"])
        )
        if existing:
            rows.append(existing)
            continue

        row = Availability(
            day_of_week=item["day_of_week"],
            opening_time=item["opening_time"],
            closing_time=item["closing_time"],
            slot_duration_minutes=30,
            active=True,
        )
        session.add(row)
        session.flush()
        rows.append(row)
    return rows


def seed_bookings(
    session,
    customers: list[Customer],
    vehicles: list[Vehicle],
    services: dict[str, Service],
) -> list[Booking]:
    today = date.today()
    slots = [
        (today - timedelta(days=7), time(10, 0), BookingStatus.COMPLETED, BookingSource.VOICE, "Basic Wash"),
        (today - timedelta(days=3), time(14, 30), BookingStatus.COMPLETED, BookingSource.DASHBOARD, "Premium Wash"),
        (today - timedelta(days=1), time(11, 0), BookingStatus.CANCELLED, BookingSource.VOICE, "Full Detailing"),
        (today, time(9, 30), BookingStatus.CONFIRMED, BookingSource.VOICE, "Basic Wash"),
        (today, time(15, 0), BookingStatus.PENDING, BookingSource.DASHBOARD, "Premium Wash"),
        (today + timedelta(days=1), time(10, 30), BookingStatus.CONFIRMED, BookingSource.VOICE, "Basic Wash"),
        (today + timedelta(days=2), time(12, 0), BookingStatus.CONFIRMED, BookingSource.DASHBOARD, "Full Detailing"),
        (today + timedelta(days=4), time(16, 0), BookingStatus.PENDING, BookingSource.VOICE, "Premium Wash"),
    ]

    bookings: list[Booking] = []
    for index, (booking_date, booking_time, status, source, service_name) in enumerate(slots):
        customer = customers[index % len(customers)]
        vehicle = vehicles[index % len(vehicles)]
        service = services[service_name]

        existing = session.scalar(
            select(Booking).where(
                Booking.customer_id == customer.id,
                Booking.booking_date == booking_date,
                Booking.booking_time == booking_time,
            )
        )
        if existing:
            bookings.append(existing)
            continue

        booking = Booking(
            customer_id=customer.id,
            vehicle_id=vehicle.id,
            service_id=service.id,
            booking_date=booking_date,
            booking_time=booking_time,
            status=status,
            source=source,
            notes=f"Seeded booking for {service_name}",
        )
        session.add(booking)
        session.flush()
        bookings.append(booking)
    return bookings


def seed_call_logs(session, customers: list[Customer], bookings: list[Booking]) -> list[CallLog]:
    now = datetime.now(timezone.utc)
    specs = [
        {
            "call_id": "seed-call-001",
            "customer": customers[0],
            "phone": customers[0].phone,
            "started_at": now - timedelta(days=2, hours=3),
            "duration_seconds": 145,
            "outcome": CallOutcome.BOOKING_CREATED,
            "booking": bookings[3] if len(bookings) > 3 else None,
        },
        {
            "call_id": "seed-call-002",
            "customer": customers[1],
            "phone": customers[1].phone,
            "started_at": now - timedelta(days=1, hours=5),
            "duration_seconds": 92,
            "outcome": CallOutcome.INFORMATION_REQUEST,
            "booking": None,
        },
        {
            "call_id": "seed-call-003",
            "customer": customers[2],
            "phone": customers[2].phone,
            "started_at": now - timedelta(hours=8),
            "duration_seconds": 210,
            "outcome": CallOutcome.CANCELLED,
            "booking": bookings[2] if len(bookings) > 2 else None,
        },
        {
            "call_id": "seed-call-004",
            "customer": None,
            "phone": "+92-300-0000099",
            "started_at": now - timedelta(hours=2),
            "duration_seconds": 67,
            "outcome": CallOutcome.NO_BOOKING,
            "booking": None,
        },
        {
            "call_id": "seed-call-005",
            "customer": customers[4],
            "phone": customers[4].phone,
            "started_at": now - timedelta(minutes=45),
            "duration_seconds": 118,
            "outcome": CallOutcome.BOOKING_CREATED,
            "booking": bookings[5] if len(bookings) > 5 else None,
        },
    ]

    logs: list[CallLog] = []
    for spec in specs:
        existing = session.scalar(select(CallLog).where(CallLog.call_id == spec["call_id"]))
        if existing:
            logs.append(existing)
            continue

        log = CallLog(
            call_id=spec["call_id"],
            customer_id=spec["customer"].id if spec["customer"] else None,
            phone=spec["phone"],
            started_at=spec["started_at"],
            duration_seconds=spec["duration_seconds"],
            outcome=spec["outcome"],
            booking_id=spec["booking"].id if spec["booking"] else None,
        )
        session.add(log)
        session.flush()
        logs.append(log)
    return logs


def run_seed() -> None:
    session = SessionLocal()
    try:
        if is_seeded(session):
            print("Seed data already exists — skipping.")
            return

        admin = seed_admin(session)
        services = seed_services(session)
        customers = seed_customers(session)
        vehicles = seed_vehicles(session, customers)
        availability = seed_availability(session)
        bookings = seed_bookings(session, customers, vehicles, services)
        call_logs = seed_call_logs(session, customers, bookings)

        session.commit()

        print("Seed completed successfully.")
        print(f"  Admin user: {admin.email}")
        print(f"  Services: {len(services)}")
        print(f"  Customers: {len(customers)}")
        print(f"  Vehicles: {len(vehicles)}")
        print(f"  Availability rows: {len(availability)}")
        print(f"  Bookings: {len(bookings)}")
        print(f"  Call logs: {len(call_logs)}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def verify_seed() -> None:
    session = SessionLocal()
    try:
        counts = {
            "users": len(session.scalars(select(User)).all()),
            "customers": len(session.scalars(select(Customer)).all()),
            "vehicles": len(session.scalars(select(Vehicle)).all()),
            "services": len(session.scalars(select(Service)).all()),
            "availability": len(session.scalars(select(Availability)).all()),
            "bookings": len(session.scalars(select(Booking)).all()),
            "call_logs": len(session.scalars(select(CallLog)).all()),
        }
        print("Database verification:")
        for table, count in counts.items():
            print(f"  {table}: {count}")
    finally:
        session.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--verify":
        verify_seed()
    else:
        run_seed()
