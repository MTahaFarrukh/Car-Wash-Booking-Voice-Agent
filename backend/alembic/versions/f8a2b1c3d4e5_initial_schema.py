"""initial_schema

Revision ID: f8a2b1c3d4e5
Revises:
Create Date: 2026-08-18

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f8a2b1c3d4e5"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

booking_status_enum = postgresql.ENUM(
    "pending",
    "confirmed",
    "completed",
    "cancelled",
    "no_show",
    name="booking_status",
    create_type=False,
)
booking_source_enum = postgresql.ENUM(
    "voice",
    "dashboard",
    name="booking_source",
    create_type=False,
)
call_outcome_enum = postgresql.ENUM(
    "booking_created",
    "information_request",
    "cancelled",
    "no_booking",
    name="call_outcome",
    create_type=False,
)


def upgrade() -> None:
    booking_status_enum.create(op.get_bind(), checkfirst=True)
    booking_source_enum.create(op.get_bind(), checkfirst=True)
    call_outcome_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_customers_phone"), "customers", ["phone"], unique=True)

    op.create_table(
        "services",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "availability",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("opening_time", sa.Time(), nullable=False),
        sa.Column("closing_time", sa.Time(), nullable=False),
        sa.Column("slot_duration_minutes", sa.Integer(), nullable=False, server_default=sa.text("30")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_availability_day_of_week"), "availability", ["day_of_week"], unique=False)

    op.create_table(
        "vehicles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vehicle_type", sa.String(length=100), nullable=False),
        sa.Column("make", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("registration_number", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_vehicles_customer_id"), "vehicles", ["customer_id"], unique=False)

    op.create_table(
        "bookings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_date", sa.Date(), nullable=False),
        sa.Column("booking_time", sa.Time(), nullable=False),
        sa.Column(
            "status",
            booking_status_enum,
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "source",
            booking_source_enum,
            nullable=False,
            server_default="dashboard",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_bookings_booking_date"), "bookings", ["booking_date"], unique=False)
    op.create_index(op.f("ix_bookings_customer_id"), "bookings", ["customer_id"], unique=False)
    op.create_index(op.f("ix_bookings_service_id"), "bookings", ["service_id"], unique=False)
    op.create_index(op.f("ix_bookings_status"), "bookings", ["status"], unique=False)
    op.create_index(op.f("ix_bookings_vehicle_id"), "bookings", ["vehicle_id"], unique=False)

    op.create_table(
        "call_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("call_id", sa.String(length=128), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column(
            "outcome",
            call_outcome_enum,
            nullable=False,
            server_default="no_booking",
        ),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_call_logs_booking_id"), "call_logs", ["booking_id"], unique=False)
    op.create_index(op.f("ix_call_logs_call_id"), "call_logs", ["call_id"], unique=True)
    op.create_index(op.f("ix_call_logs_customer_id"), "call_logs", ["customer_id"], unique=False)
    op.create_index(op.f("ix_call_logs_started_at"), "call_logs", ["started_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_call_logs_started_at"), table_name="call_logs")
    op.drop_index(op.f("ix_call_logs_customer_id"), table_name="call_logs")
    op.drop_index(op.f("ix_call_logs_call_id"), table_name="call_logs")
    op.drop_index(op.f("ix_call_logs_booking_id"), table_name="call_logs")
    op.drop_table("call_logs")

    op.drop_index(op.f("ix_bookings_vehicle_id"), table_name="bookings")
    op.drop_index(op.f("ix_bookings_status"), table_name="bookings")
    op.drop_index(op.f("ix_bookings_service_id"), table_name="bookings")
    op.drop_index(op.f("ix_bookings_customer_id"), table_name="bookings")
    op.drop_index(op.f("ix_bookings_booking_date"), table_name="bookings")
    op.drop_table("bookings")

    op.drop_index(op.f("ix_vehicles_customer_id"), table_name="vehicles")
    op.drop_table("vehicles")

    op.drop_index(op.f("ix_availability_day_of_week"), table_name="availability")
    op.drop_table("availability")

    op.drop_table("services")

    op.drop_index(op.f("ix_customers_phone"), table_name="customers")
    op.drop_table("customers")

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

    call_outcome_enum.drop(op.get_bind(), checkfirst=True)
    booking_source_enum.drop(op.get_bind(), checkfirst=True)
    booking_status_enum.drop(op.get_bind(), checkfirst=True)
