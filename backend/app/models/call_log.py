"""AI voice call log metadata."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enum_utils import enum_values


class CallOutcome(str, enum.Enum):
    BOOKING_CREATED = "booking_created"
    INFORMATION_REQUEST = "information_request"
    CANCELLED = "cancelled"
    NO_BOOKING = "no_booking"


class CallLog(Base):
    __tablename__ = "call_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    provider: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    outcome: Mapped[CallOutcome] = mapped_column(
        Enum(CallOutcome, name="call_outcome", values_callable=enum_values),
        default=CallOutcome.NO_BOOKING,
        nullable=False,
    )
    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="SET NULL"), nullable=True, index=True
    )

    customer: Mapped["Customer | None"] = relationship(back_populates="call_logs")
    booking: Mapped["Booking | None"] = relationship(back_populates="call_logs")


from app.models.booking import Booking  # noqa: E402
from app.models.customer import Customer  # noqa: E402
