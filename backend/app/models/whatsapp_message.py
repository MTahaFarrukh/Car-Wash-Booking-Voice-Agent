"""Persisted WhatsApp message idempotency records."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class WhatsAppProcessedMessage(Base):
    """Tracks processed WhatsApp message IDs to prevent duplicate handling."""

    __tablename__ = "whatsapp_processed_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    sender_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    response_message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
