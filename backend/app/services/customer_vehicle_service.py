"""Customer/vehicle domain services reused by APIs and agent tools."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import CustomerNotFoundError, InvalidBookingError, VehicleNotFoundError
from app.models.customer import Customer
from app.models.vehicle import Vehicle


class CustomerVehicleService:
    """Manage customers and vehicles as domain operations."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def find_customer_by_phone(self, phone: str) -> Customer | None:
        return self.db.scalar(select(Customer).where(Customer.phone == phone))

    def get_customer(self, customer_id: uuid.UUID) -> Customer:
        customer = self.db.get(Customer, customer_id)
        if customer is None:
            raise CustomerNotFoundError(f"Customer {customer_id} not found")
        return customer

    def create_customer(self, *, name: str, phone: str, email: str | None = None) -> Customer:
        existing = self.find_customer_by_phone(phone)
        if existing is not None:
            raise InvalidBookingError("Customer phone already exists")

        customer = Customer(name=name, phone=phone, email=email)
        self.db.add(customer)
        self.db.commit()
        self.db.refresh(customer)
        return customer

    def find_or_create_customer(self, *, name: str, phone: str, email: str | None = None) -> Customer:
        existing = self.find_customer_by_phone(phone)
        if existing is not None:
            # Upgrade placeholder WhatsApp names when the customer later gives a real name.
            placeholder = existing.name.lower().startswith("whatsapp customer")
            if placeholder and name and not name.lower().startswith("whatsapp customer"):
                existing.name = name
                if email is not None:
                    existing.email = email
                self.db.commit()
                self.db.refresh(existing)
            return existing
        return self.create_customer(name=name, phone=phone, email=email)

    def update_customer(
        self,
        customer_id: uuid.UUID,
        *,
        name: str | None = None,
        phone: str | None = None,
        email: str | None = None,
    ) -> Customer:
        customer = self.get_customer(customer_id)
        if name is not None:
            customer.name = name
        if phone is not None:
            customer.phone = phone
        if email is not None:
            customer.email = email
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise InvalidBookingError("Customer phone already exists") from exc
        self.db.refresh(customer)
        return customer

    def get_vehicle(self, vehicle_id: uuid.UUID) -> Vehicle:
        vehicle = self.db.get(Vehicle, vehicle_id)
        if vehicle is None:
            raise VehicleNotFoundError(f"Vehicle {vehicle_id} not found")
        return vehicle

    def list_customer_vehicles(self, customer_id: uuid.UUID) -> list[Vehicle]:
        self.get_customer(customer_id)
        return list(
            self.db.scalars(
                select(Vehicle)
                .where(Vehicle.customer_id == customer_id)
                .order_by(Vehicle.created_at.desc())
            ).all()
        )

    def create_vehicle(
        self,
        customer_id: uuid.UUID,
        *,
        vehicle_type: str,
        make: str,
        model: str,
        registration_number: str | None = None,
    ) -> Vehicle:
        self.get_customer(customer_id)
        vehicle = Vehicle(
            customer_id=customer_id,
            vehicle_type=vehicle_type,
            make=make,
            model=model,
            registration_number=registration_number,
        )
        self.db.add(vehicle)
        self.db.commit()
        self.db.refresh(vehicle)
        return vehicle

    def update_vehicle(
        self,
        vehicle_id: uuid.UUID,
        *,
        vehicle_type: str | None = None,
        make: str | None = None,
        model: str | None = None,
        registration_number: str | None = None,
    ) -> Vehicle:
        vehicle = self.get_vehicle(vehicle_id)
        if vehicle_type is not None:
            vehicle.vehicle_type = vehicle_type
        if make is not None:
            vehicle.make = make
        if model is not None:
            vehicle.model = model
        if registration_number is not None:
            vehicle.registration_number = registration_number
        self.db.commit()
        self.db.refresh(vehicle)
        return vehicle
